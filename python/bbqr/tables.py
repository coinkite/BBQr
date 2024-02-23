#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#
# Print a table used in the spec. Use "bbqr table" to view.
#
import pyqrcode
from math import ceil, floor
from .utils import version_to_chars
from .consts import HEADER_LEN

def dump_table():
    ver_size = pyqrcode.tables.version_size

    hdr = "Vers | Pixels  | Chars |  Hex |  Base32 | 2xBase32 | 5xBase32 | 10xBase32"
    print(hdr)
    print('|'.join('-'*len(i) for i in hdr.split('|')))

    for v in range(1, 41):
        chars = version_to_chars(v)
        if chars < 1500 and v not in {1, 11, 14}: continue

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

# EOF
