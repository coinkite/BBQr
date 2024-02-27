#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
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
from .utils import version_to_chars, encode_data, decode_data, int2base36
from .consts import HEADER_LEN, KNOWN_FILETYPES

def num_qr_needed(ver, ll, split_mod):
    # Determine number of QR's at indicated version would be
    # needed to hold ll characters. when 2 or more QR, consider
    # the exact split point cannot be between encoded symbols
    # - ok to return huge numbers for unlikely cases
    cap = version_to_chars(ver) - HEADER_LEN
    cap2 = cap - (cap % split_mod)

    need = ceil(ll / cap2)

    if need == 1:
        # no alignment concerns
        assert ll <= cap
        return 1, ll

    # going to be 2 or more, gotta be precise
    actual = ((need - 1) * cap2) + cap

    return (need if actual >= ll else (need + 1)), cap2

def find_best_version(ll, split_mod, min_split=1, max_split=1295, min_version=5, max_version=40):
    # Find ideal QR version and provide # of QR and splits needed.
    # - assumes you want to pack the QR, so forcing min_split means you need to have the data
    #   at least the data to fill that # of QR at min_version
    #
    # ll = length of encoded data to be transmitted (no headers)
    # split_mod = required size of non-runt parts so that can be decoded w/o spliting symbols

    min_version = min(min_version, max_version)     # in case they spec a very low max

    assert 1 <= min_version <= max_version <= 40, "min/max version out of range"
    assert 1 <= min_split <= max_split <= 1295, "num splits out of range"

    options = []
    for ver in range(min_version, max_version+1):
        count, pe = num_qr_needed(ver, ll, split_mod)
        if not (min_split <= count <= max_split): continue
        options.append( (ver, count, pe) )

    # pick smallest number of QR, lowest version
    options.sort(key=lambda v: (v[1], v[0]))

    if not options:
        raise ValueError("Cannot make it fit")

    return options[0]

def split_qrs(raw, type_code, encoding=None, **kws):
    # Take some bytes and yield a series of text values that 
    # can be sent as QR code.
    # - returns text
    # - assumes and requires alnum, L error level
    # - see find_best_version() for additional kw args

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
                    + int2base36(num_qr) + int2base36(n)
                    + encoded[off:off+per_each] for
                            (n, off) in enumerate(range(0, ll, per_each))]

# EOF
