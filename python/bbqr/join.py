#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#
# - joins QR codes
#
import re
from .utils import decode_data
from .consts import HEADER_LEN, KNOWN_FILETYPES, MAX_SIZE

# strict header grammar: B$ magic, known encoding, one uppercase letter of
# file type, then uppercase base-36 digits for part count and index
HEADER_RE = re.compile(r'\AB\$[H2Z][A-Z][0-9A-Z]{2}[0-9A-Z]{2}\Z')

def join_qrs(parts, max_size=MAX_SIZE):
    # take a bunch of scanned data.
    # - put into order, decode, return type code and raw data bytes
    # - lazy desktop code here
    hdr = set()
    for p in parts:
        assert HEADER_RE.match(p[0:HEADER_LEN]), f'invalid header: {p[0:HEADER_LEN]!r}'
        assert len(p) > HEADER_LEN, 'empty body'
        hdr.add(p[0:6])
    assert len(hdr) == 1, 'conflicting/variable filetype/encodings/sizes'
    hdr = hdr.pop()

    assert hdr[0:2] == 'B$', 'fixed header not found, expected B$'
    encoding = hdr[2]
    file_type = hdr[3]
    num_parts = int(hdr[4:6], 36)

    assert num_parts >= 1, 'zero parts?'
    assert encoding in 'H2Z', f'bad encoding: {encoding}'

    # ok to have dups here, just need them all
    data = {}
    body_len = None
    for p in parts:
        idx = int(p[6:8], 36)
        assert idx < num_parts, f'got part {idx} but only expecting {num_parts}'

        if idx in data:
            assert data[idx] == p[8:], f'dup part 0x{idx:02x} has wrong content'
        else:
            data[idx] = p[8:]

        if idx != num_parts - 1:
            # all non-final bodies must share one length
            if body_len is None:
                body_len = len(p) - HEADER_LEN
            assert len(p) - HEADER_LEN == body_len, 'non-final parts must have equal length'

    missing = set(range(num_parts)) - set(data)
    assert not missing, f'parts missing: {missing!r}'

    if num_parts > 1:
        # final body must be no longer than the others
        assert len(data[num_parts - 1]) <= body_len, 'final part too long'

    parts = [data[i] for i in range(num_parts)]

    raw = decode_data(parts, encoding, max_size)

    assert raw, 'empty transfer'

    # maybe: decode objects here... U=>text, C=>obj, J=>obj

    return file_type, raw

# EOF
