#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#
# - helpers and basics
#
import re, zlib
from base64 import b32encode, b32decode
from .consts import MAX_SIZE

HEX_RE = re.compile(r'\A[0-9A-F]*\Z')

def version_to_chars(v):
    # return number of **chars** that fit into indicated version QR
    # - assumes L for ECC
    # - assumes alnum encoding
    import pyqrcode

    assert 1 <= v <= 40
    ecc = "L"
    encoding = 2        # alnum

    return pyqrcode.tables.data_capacity[v][ecc][encoding]

def int2base36(n):
    # convert an integer to two digits of base 36 string. 00 thu ZZ
    # converse is just int(s, base=36)
    assert 0 <= n <= 1295

    tostr = lambda x: chr(48+x) if x < 10 else chr(65+x-10)

    a, b = divmod(n, 36)

    return tostr(a) + tostr(b)

def encode_data(raw, encoding=None):
    # return new encoding (if we upgraded) and the
    # characters after encoding (a string)
    # - default is Zlib or if compression doesn't help, base32
    # - returned data can be split, but must be done modX where X provided

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

    # Default: base32 encoding, no padding bytes
    data = b32encode(raw).decode('ascii').rstrip('=')

    return encoding, data, 8

def scan_deflate_distances(stream, max_dist=1024):
    # Validate-only parse of a raw DEFLATE stream (RFC 1951): every
    # back-reference distance must fit max_dist and the output so far.
    # zlib cannot check this itself: its strict window check is compiled
    # out (INFLATE_STRICT) and CPython exposes no knob for it.
    LEN_BASE = [3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,
                67,83,99,115,131,163,195,227,258]
    LEN_EXTRA = [0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0]
    DIST_BASE = [1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,
                 1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
    DIST_EXTRA = [0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]
    CLC_ORDER = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]

    idx, bitbuf, bitcnt = 0, 0, 0

    def bits(n):
        nonlocal idx, bitbuf, bitcnt
        while bitcnt < n:
            assert idx < len(stream), 'incomplete DEFLATE stream'
            bitbuf |= stream[idx] << bitcnt
            idx += 1
            bitcnt += 8
        rv = bitbuf & ((1 << n) - 1)
        bitbuf >>= n
        bitcnt -= n
        return rv

    def build(lengths):
        # canonical Huffman code table: (num bits, code) => symbol
        table = {}
        code = 0
        for ln in range(1, 16):
            for sym, l in enumerate(lengths):
                if l == ln:
                    table[(ln, code)] = sym
                    code += 1
            code <<= 1
        return table

    def decode(table):
        ln = code = 0
        while True:
            code = (code << 1) | bits(1)
            ln += 1
            assert ln <= 15, 'bad Huffman code'
            if (ln, code) in table:
                return table[(ln, code)]

    produced = 0
    while True:
        final = bits(1)
        btype = bits(2)
        assert btype != 3, 'bad block type'

        if btype == 0:
            # stored block: byte-align, LEN/NLEN, skip contents
            bits(bitcnt % 8)
            idx -= bitcnt // 8
            bitbuf = bitcnt = 0
            assert idx + 4 <= len(stream), 'incomplete DEFLATE stream'
            ln = stream[idx] | (stream[idx+1] << 8)
            nlen = stream[idx+2] | (stream[idx+3] << 8)
            assert ln ^ nlen == 0xFFFF, 'bad stored block'
            idx += 4
            assert idx + ln <= len(stream), 'incomplete DEFLATE stream'
            idx += ln
            produced += ln
        else:
            if btype == 1:
                lit = build([8]*144 + [9]*112 + [7]*24 + [8]*8)
                dist = build([5]*32)
            else:
                hlit = bits(5) + 257
                hdist = bits(5) + 1
                hclen = bits(4) + 4
                cl_lens = [0] * 19
                for i in range(hclen):
                    cl_lens[CLC_ORDER[i]] = bits(3)
                cl = build(cl_lens)
                lens = []
                while len(lens) < hlit + hdist:
                    sym = decode(cl)
                    if sym < 16:
                        lens.append(sym)
                    elif sym == 16:
                        assert lens, 'bad code lengths'
                        lens += [lens[-1]] * (3 + bits(2))
                    elif sym == 17:
                        lens += [0] * (3 + bits(3))
                    else:
                        lens += [0] * (11 + bits(7))
                assert len(lens) == hlit + hdist, 'bad code lengths'
                lit = build(lens[:hlit])
                dist = build(lens[hlit:])

            while True:
                sym = decode(lit)
                if sym == 256:
                    break
                if sym < 256:
                    produced += 1
                    continue
                assert sym <= 285, 'bad length code'
                length = LEN_BASE[sym-257] + bits(LEN_EXTRA[sym-257])
                dsym = decode(dist)
                assert dsym <= 29, 'bad distance code'
                d = DIST_BASE[dsym] + bits(DIST_EXTRA[dsym])
                assert d <= produced, 'invalid distance too far back'
                assert d <= max_dist, 'distance exceeds window'
                produced += length

        if final:
            break

def decode_data(parts, encoding, max_size=MAX_SIZE):
    # give back the bytes after decoding
    # - already in order
    # - keeps the parts separate here to validate correct split from encoder
    if encoding == 'H':
        rv = b''
        for p in parts:
            assert HEX_RE.match(p), 'non-canonical hex body'
            rv += bytes.fromhex(p)
        assert len(rv) <= max_size, 'decoded data too large'
        return rv

    # base32 decode, but insert padding for API
    rv = b''
    for n, p in enumerate(parts):
        residue = len(p) % 8
        is_final = (n == len(parts) - 1)
        bad_length = residue in (1, 3, 6) if is_final else residue != 0
        assert not bad_length, 'invalid Base32 body length'

        padding = (8 - residue) % 8
        here = b32decode(p + (padding*'='))
        # non-zero pad bits in the final Base32 symbol are non-canonical
        assert b32encode(here).decode('ascii').rstrip('=') == p, 'non-canonical Base32 body'
        rv += here

    assert len(rv) <= max_size, 'decoded data too large'

    if encoding == 'Z':
        # exact 1k window enforcement, which zlib alone cannot provide
        scan_deflate_distances(rv)

        # decompress in 1k chunks so the size cap applies while inflating,
        # instead of after the full output has been buffered
        z = zlib.decompressobj(wbits=-10)
        chunks = []
        total = 0
        while rv and not z.eof:
            here = z.decompress(rv, 1024)
            total += len(here)
            assert total <= max_size, 'decompressed data too large'
            chunks.append(here)
            rv = z.unconsumed_tail
        chunks.append(z.flush())
        assert z.eof, 'incomplete DEFLATE stream'
        assert not z.unused_data, 'trailing data after DEFLATE stream'
        rv = b''.join(chunks)

    return rv
        

# EOF
