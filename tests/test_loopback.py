
from context import bbqr
import pytest
import os


@pytest.mark.parametrize('encoding', [None]+list('H2Z'))
@pytest.mark.parametrize('size', [10, 100, 2000, 10_000, 50_000] + list(range(4000, 5500)))
#@pytest.mark.parametrize('size', [10, 100, 2000, 50_000])
#@pytest.mark.parametrize('min_split', [1, 2, 10])
@pytest.mark.parametrize('max_version', [11, 29, 40])
@pytest.mark.parametrize('low_ent', [True, False])
def test_loopback(encoding, size, max_version, low_ent, filetype='P', min_split=1):

    if low_ent:
        data = b'A'*size
    else:
        data = os.urandom(size)
    
    vers, parts = bbqr.split_qrs(data, filetype, encoding=encoding,
                                    min_split=min_split, max_version=max_version)
    assert vers <= max_version
    np = len(parts)
    assert np >= min_split

    if encoding is not None and parts[0][2] != encoding:
        assert encoding == 'Z'

    xtype, readback = bbqr.join_qrs(parts)

    assert xtype == filetype
    assert readback == data

# EOF
