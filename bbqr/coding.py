#
# (c) Copyright 2023 by Coinkite Inc. This file is put in the public domain.
#
# - uses pyqrcode for deep QR knowledge
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
from .utils import version_to_chars, encode_data, decode_data
from .consts import HEADER_LEN, KNOWN_FILETYPES


def find_best_version(ll, split_mod, min_split=1, max_split=255, min_version=5, max_version=40):
    # ll = length of encoded data to be transmitted (no headers)
    # v23 = 794 bytes capacity
    # v27 = 1066 bytes capacity is a sweet spot w/ 1k+ each

    min_version = min(min_version, max_version)     # in case they spec a very low max

    assert 1 <= min_version <= max_version <= 40, "min/max version out of range"
    assert 1 <= min_split <= max_split <= 255, "num splits out of range"

    # search for a version that will hold whole thing, or if split in two, etc
    # - this is optimum *number* of QR, but perhaps more dense than needed
    for num_qr in range(min_split, max_split+1):
        for ver in range(min_version, max_version+1):
            # capacity at this size
            cap = version_to_chars(ver) - HEADER_LEN

            per_each = cap          #floor(cap / num_qr)

            # need to split along correct boundaries
            # depending on encoding type
            if num_qr > 1:
                per_each -= per_each % split_mod

            runt_size = ll - (per_each * (num_qr - 1))
            assert runt_size >= 0

            if runt_size > cap:
                # it cannot fit
                continue

            if num_qr * per_each < ll:
                continue

            return ver, num_qr, per_each
    else:
        raise ValueError("Cannot make it fit")


def split_qrs(raw, type_code, encoding=None, **kws):
    # Take some bytes and yield a series of text values that 
    # can be sent as QR code.
    # - returns text
    # - assumes and requires alnum, L error level
    # - see find_best_version for additional kw args

    assert type_code in KNOWN_FILETYPES, f"invalid type_code: {type_code}"
    if encoding: assert encoding in 'H2Z', f"invalid encoding: {encoding}"
    if not isinstance(raw, bytes):
        assert isinstance(raw, str), "need binary or text"
        raw = raw.encode('utf-8')

    # perhaps compress data
    encoding, encoded, split_mod = encode_data(raw, encoding)

    ll = len(encoded)

    ver, num_qr, per_each = find_best_version(ll, split_mod, **kws)

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
    

if __name__ == '__main__':
    # smoke test only
    ver, parts = split_qrs(b'a'*2148, 'P', encoding='Z', min_split=1, max_split=99,
                            min_version=11, max_version=40)
    print(f'{len(parts)} parts, version={ver}, headers:', end='\n\t')
    print('\n\t'.join(f'{i[0:20]}  {len(i)} len' for i in parts))

    #qs = [pyqrcode.create(p, error='L', version=ver, mode='alphanumeric') for p in parts]

    ft, raw = join_qrs(parts)


# EOF
