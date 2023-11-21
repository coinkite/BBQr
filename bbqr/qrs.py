#
# (c) Copyright 2023 by Coinkite Inc. This file is covered by license found in COPYING-CC.
#
# - requires pyqrcode and Pillow for images
# - text prefix on each QR:
#
#       B$                  fixed header for this protocol (2 chars)
#       2                   one char encode: Z=zlib, 2=Base32, H=Hex
#       P                   one char file type: P=PSBT, T=TXN, etc
#       05                  2-digits of HEX: total number of QR codes
#       00                  2-digits of HEX: which QR code this is in the sequence
#
import pyqrcode, zlib
from math import ceil, floor
from base64 import b32encode, b32decode

# Standard defines a fixed-length header
HEADER_LEN = 8

# Codes for PSBT vs. TXN and so on
KNOWN_FILETYPES = 'PTJCU'

def version_to_chars(v):
    # return number of **chars** that fit into indicated version QR
    # - assumes L for ECC
    # - assumes alnum encoding
    assert 1 <= v <= 40
    ecc = "L"
    encoding = 2        # alnum

    return pyqrcode.tables.data_capacity[v][ecc][encoding]

def dump_table():
    ver_size = pyqrcode.tables.version_size

    hdr = "Vers | Pixels  | Chars |  Hex |  Base32 | 2*Base32 | 5*Base32 | 10*Base32"
    print(hdr)
    print('|'.join('-'*len(i) for i in hdr.split('|')))

    for v in range(1, 41):
        chars = version_to_chars(v)
        if chars < 1500 and v not in {1, 11}: continue

        sz = ver_size[v]
        cap = (chars - HEADER_LEN)
        bys = floor(cap / 2)       # HEX encoding
        b32 = floor((cap // 8) * 5)
        print(f' {v:2}  | {sz:3}x{sz:<3d} |  {chars:4d} ', end='')
        print(f'| {bys:5d}', end='')
        print(f'| {b32:7d}', end='')

        for sp in [2, 5, 10]:
            mx = b32 * sp
            print(f' | {mx:8d}', end='')

        print("")

def encode_data(raw, encoding=None):
    # return new encoding (if we upgraded) and the
    # characters after encoding (a string)
    # - default is Zlib or if compression doesn't help, base32

    if encoding == 'H':
        # Hex mode is easy.
        return encoding, raw.hex().upper(), 2

    if not encoding or encoding == 'Z':
        # Trial compression, but skip if it embiggens the data
        z = zlib.compressobj(wbits=-10)
        cmp = z.compress(raw)
        cmp += z.flush()
        if len(cmp) >= len(raw):
            encoding = '2'
        else:
            encoding = 'Z'
            raw = cmp

    data = b32encode(raw).decode('ascii').rstrip('=')

    return encoding, data, 5

def decode_data(parts, encoding):
    # give back the bytes after decoding
    # - already in order
    # - keeps the parts separate here to validate correct split from encoder
    if encoding == 'H':
        return b''.join(bytes.fromhex(p) for p in parts)

    # base32 decode, but insert padding for API
    rv = b''
    for p in parts:
        padding = (8 - (len(p) % 8)) % 8
        rv += b32decode(p + (padding*'='))

    if encoding == 'Z':
        # decompress
        z = zlib.decompressobj(wbits=-10)
        rv = z.decompress(rv)
        rv += z.flush()

    return rv
        

def split_qrs(raw, type_code, encoding=None,
                min_split=1, max_split=20, min_version=23, max_version=40):
    # Take some bytes and yield a series of text values that 
    # can be sent as QR code.
    # - returns text
    # - assumes and requires alnum, L error level
    assert type_code in KNOWN_FILETYPES, f"invalid type_code: {type_code}"
    assert 1 <= min_version <= max_version <= 40, "min/max version out of range"
    assert encoding in 'H2Z', f"invalid encoding: {encoding}"
    if not isinstance(raw, bytes):
        assert isinstance(raw, str), "need binary or text"
        raw = raw.encode('utf-8')

    # perhaps compress data
    encoding, encoded, split_mod = encode_data(raw, encoding)

    ll = len(encoded)

    # v23 = 794 bytes capacity
    # v27 = 1066 bytes capacity is a sweet spot w/ 1k+ each
    min_version = min(min_version, max_version)
    for ver in range(min_version, max_version+1):
        if ver > max_version: continue

        cap = version_to_chars(ver) - HEADER_LEN
        if cap >= ll:
            num_qr = 1
            per_each = ll
            break

        num_qr = max(ceil(ll / cap), min_split)
        per_each = ceil(ll / num_qr)

        # need to split along correct boundaries
        # depending on encoding type
        per_each -= per_each % split_mod

        runt_size = ll - (per_each * (num_qr - 1))
        assert runt_size >= 0

        if runt_size > cap:
            # unlikely, but might happen if very close
            continue

        if min_split <= num_qr <= max_split:
            break
    else:
        raise ValueError("Cannot make it fit")

    assert per_each * num_qr >= ll

    return ver, [f'B${encoding}{type_code}' 
                        + f'{num_qr:02x}{n:02x}'.upper() 
                        + encoded[off:off+per_each] for
                                (n, off) in enumerate(range(0, ll, per_each))]

def join_qrs(parts):
    # take a bunch of scanned data. 
    # - put into order, decode, return type code and raw data bytes
    # - lazy desktop code here
    hdr = {p[0:6] for p in parts}
    assert len(hdr) == 1, 'conflicting/variable filetype/encodings/sizes'
    hdr = hdr.pop()

    assert hdr[0:2] == 'B$', 'fixed header not found, expected B$'
    encoding = hdr[2]
    file_type = hdr[3]
    num_parts = int(hdr[4:6], 16)

    assert num_parts >= 1, 'zero parts?'
    assert encoding in 'H2Z', f'bad encoding: {encoding}'
    assert file_type in KNOWN_FILETYPES, f'bad file type: {encoding}'

    # ok to have dups here, just need them all
    data = {}
    for p in parts:
        idx = int(p[6:8], 16)
        assert idx < num_parts, f'got part {idx} but only expecting {num_parts}'

        if idx in data:
            assert data[idx] == p[8:], f'dup part 0x{idx:02x} has wrong content'
        else:
            data[idx] = p[8:]

    missing = set(range(num_parts)) - set(data)
    assert not missing, f'parts missing: {missing:r}'

    parts = [data[i] for i in range(num_parts)]

    raw = decode_data(parts, encoding)

    return file_type, raw
    

if 1 and __name__ == '__main__':
    dump_table()

if 0 and __name__ == '__main__':
    ver, parts = split_qrs(b'a'*2148, 'P', encoding='Z', min_split=1, max_split=99,
                            min_version=11, max_version=40)
    print(f'{len(parts)} parts, version={ver}, headers:', end='\n\t')
    print('\n\t'.join(f'{i[0:20]}  {len(i)} len' for i in parts))

    #qs = [pyqrcode.create(p, error='L', version=ver, mode='alphanumeric') for p in parts]

    ft, raw = join_qrs(parts)


# EOF
