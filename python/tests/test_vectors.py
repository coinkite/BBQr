#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#

from context import bbqr
import pytest, json, hashlib, zlib

with open('../test_data/bip-test-vectors.json') as f:
    DOC = json.load(f)

@pytest.mark.parametrize('vec', DOC['vectors'], ids=lambda v: v['name'])
def test_positive_vectors(vec):
    for frames in (vec['frames'], list(reversed(vec['frames']))):
        file_type, raw = bbqr.join_qrs(frames)
        assert file_type == vec['file_type']
        assert len(raw) == vec['input_length']
        assert hashlib.sha256(raw).hexdigest() == vec['input_sha256']

@pytest.mark.parametrize('case', DOC['invalid_cases'], ids=lambda c: c['name'])
def test_negative_vectors(case):
    with pytest.raises((AssertionError, ValueError, zlib.error)):
        bbqr.join_qrs(case['frames'])

@pytest.mark.parametrize('case', DOC['strict_policy_cases'], ids=lambda c: c['name'])
def test_strict_policy_cases(case):
    # draft v4: receivers MAY ignore later duplicates without comparing;
    # we compare bodies and fail on conflict - stricter local policy
    with pytest.raises(AssertionError):
        bbqr.join_qrs(case['frames'])

def test_overwide_deflate_distance():
    # back-reference distance of 2048 needs a bigger window than wbits=10 allows
    frame = open('../test_data/deflate-overwide-distance.txt').read().strip()
    with pytest.raises(AssertionError, match='window'):
        bbqr.join_qrs([frame])

def test_deflate_window_boundary():
    # distance 1024 is the window maximum and must decode
    frame = open('../test_data/deflate-dist1024.txt').read().strip()
    _, raw = bbqr.join_qrs([frame])
    assert len(raw) == 2048
    assert hashlib.sha256(raw).hexdigest() == \
        'c30537f307aa7aed41677a596ea4f60de232ff2dc2ef7b478e6ae53e300db05d'

    # distance 1025 exceeds the window and must be rejected
    frame = open('../test_data/deflate-dist1025.txt').read().strip()
    with pytest.raises(AssertionError, match='window'):
        bbqr.join_qrs([frame])

def test_decompressed_size_cap():
    vec = next(v for v in DOC['vectors'] if v['name'] == 'deflate-psbt')

    # compressed input fits the cap; decompressed output must not
    with pytest.raises(AssertionError, match='too large'):
        bbqr.join_qrs(vec['frames'], max_size=vec['input_length'] - 1)

    _, raw = bbqr.join_qrs(vec['frames'])
    assert len(raw) == vec['input_length']

# EOF
