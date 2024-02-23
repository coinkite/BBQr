#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#

from context import bbqr
import pytest, os, pyqrcode

def valid_qr(ver, parts):
    # build the QR so we know it's valid: right size for version, correct chars
    for data in parts:
        q = pyqrcode.create(data, error='L', version=ver, mode='alphanumeric')

@pytest.mark.parametrize('encoding', [None]+list('H2Z'))
@pytest.mark.parametrize('size', [10, 100, 2000, 10_000, 50_000] + list(range(4000, 5500, 11)))
#@pytest.mark.parametrize('size', [10, 100, 2000, 50_000])
@pytest.mark.parametrize('max_version', [11, 29, 40])
@pytest.mark.parametrize('low_ent', [True, False])
def test_loopback(encoding, size, max_version, low_ent, filetype='P'):

    if low_ent:
        data = b'A'*size
    else:
        data = os.urandom(size)
    
    vers, parts = bbqr.split_qrs(data, filetype, encoding=encoding,
                                    min_split=1, max_version=max_version)
    assert vers <= max_version
    np = len(parts)

    if encoding is not None and parts[0][2] != encoding:
        assert encoding == 'Z'

    xtype, readback = bbqr.join_qrs(parts)
    assert xtype == filetype
    assert readback == data

    # too slow
    #valid_qr(vers, parts)

@pytest.mark.parametrize('min_split', range(2,10))
def test_min_split(min_split, size=10_000):
    data = os.urandom(size)
    vers, parts = bbqr.split_qrs(data, 'T', encoding='2', min_split=min_split)
    np = len(parts)
    assert np >= min_split

    xtype, readback = bbqr.join_qrs(parts)
    assert xtype == 'T'
    assert readback == data
    valid_qr(vers, parts)

@pytest.mark.parametrize('encoding', list('H2Z'))
@pytest.mark.parametrize('size', list(range(1060, 1080)))
@pytest.mark.parametrize('low_ent', [True, False])
def test_edge27(low_ent, encoding, size, version=27):
    if low_ent:
        data = b'A'*size
    else:
        data = os.urandom(size)

    vers, parts = bbqr.split_qrs(data, 'T', encoding=encoding,
                    max_split=2, min_version=version, max_version=version)

    assert vers == version
    count = len(parts)

    #print(f'{count=} {encoding=} {size=} {vers=}')
    if encoding == 'H':
        assert count == (1 if size <= 1062 else 2)
    elif encoding == 'Z':
        assert count == 1
        if low_ent:
            assert len(parts[0]) < 100
    elif encoding == '2':
        assert count == 1

    _, readback = bbqr.join_qrs(parts)
    assert readback == data
    #valid_qr(vers, parts)

@pytest.mark.parametrize('encoding', 'H2')
def test_maxsize(encoding):
    # Build largest possible QR series for each encoding.

    nc = 4296-8       # version 40 capacity in chars, less header
    if encoding == 'H':
        pkt_size = nc // 2
    elif encoding == '2':
        pkt_size = nc * 5 // 8

    nparts = int('ZZ', 36)       # 1295
    data = os.urandom(pkt_size * nparts)
    vers, parts = bbqr.split_qrs(data, 'T', encoding=encoding, min_version=40)

    assert vers == 40
    count = len(parts)
    assert count == nparts

    _, readback = bbqr.join_qrs(parts)
    assert readback == data
    valid_qr(vers, parts[3:4])

    print(f"Maxsize: {encoding=} => {len(data)} bytes binary")

# EOF
