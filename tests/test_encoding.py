#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#

from context import bbqr
import pytest, os, pyqrcode

@pytest.mark.parametrize('fname', [
	'data/1in1000out.psbt',
	'data/1in100out.psbt',
	'data/1in10out.psbt',
	'data/1in20out.psbt',
	'data/1in2out.psbt',
	'data/devils-txn.txn',
	'data/finalized-by-ckcc.txn',
	'data/last.txn',
	'data/nfc-result.txn',
	'data/signed.txn',
])
def test_compression(fname):
    # more of a measurement than a test...
    from bbqr.utils import encode_data, decode_data
    from base64 import b32decode

    raw = open(fname, 'rb').read()

    actual_enc, cooked, split_mod = encode_data(raw, 'Z')

    assert actual_enc == 'Z'

    chk = decode_data([cooked], actual_enc)
    assert chk == raw

    rb = decode_data([cooked], '2')

    assert len(rb) < len(raw)
    ratio = 100 - (len(rb) * 100.0 / len(raw))
    print(f'{fname}: {len(raw)} => {len(rb)} bytes, {ratio:.1f}% compression')
    

# EOF
