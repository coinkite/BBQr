#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#

from context import bbqr
import pytest, os, pyqrcode

def test_real_scan():
    lines = [ln.strip() for ln in open('data/real-scan.txt', 'rt').readlines() if ln.strip()]

    file_type, data = bbqr.join_qrs(lines)

    assert file_type == 'U'
    assert b'Zlib compressed' in data
    assert b'PSBT' in data

# EOF
