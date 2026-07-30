import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import { joinQRs } from '../src/join';

const doc = JSON.parse(
  readFileSync(new URL('../../test_data/bip-test-vectors.json', import.meta.url), 'utf-8')
);

describe('BBQr BIP draft vectors', () => {
  for (const v of doc.vectors) {
    test(`decode ${v.name}`, () => {
      for (const frames of [v.frames, [...v.frames].reverse()]) {
        const { fileType, raw } = joinQRs(frames);

        expect(fileType).toBe(v.file_type);
        expect(raw.length).toBe(v.input_length);
        expect(createHash('sha256').update(raw).digest('hex')).toBe(v.input_sha256);
      }
    });
  }

  for (const c of doc.invalid_cases) {
    test(`reject ${c.name}`, () => {
      expect(() => joinQRs(c.frames)).toThrow();
    });
  }

  // draft v4: receivers MAY ignore later duplicates without comparing;
  // we compare bodies and fail on conflict - stricter local policy
  for (const c of doc.strict_policy_cases) {
    test(`reject ${c.name} (strict local policy)`, () => {
      expect(() => joinQRs(c.frames)).toThrow();
    });
  }
});

describe('DEFLATE resource limits', () => {
  test('reject back-reference distance beyond the 1k window', () => {
    const frame = readFileSync(
      new URL('../../test_data/deflate-overwide-distance.txt', import.meta.url),
      'utf-8'
    ).trim();

    expect(() => joinQRs([frame])).toThrow(/distance/);
  });

  test('window boundary: distance 1024 accepted, 1025 rejected', () => {
    const ok = readFileSync(
      new URL('../../test_data/deflate-dist1024.txt', import.meta.url),
      'utf-8'
    ).trim();

    const { raw } = joinQRs([ok]);
    expect(raw.length).toBe(2048);
    expect(createHash('sha256').update(raw).digest('hex')).toBe(
      'c30537f307aa7aed41677a596ea4f60de232ff2dc2ef7b478e6ae53e300db05d'
    );

    const bad = readFileSync(
      new URL('../../test_data/deflate-dist1025.txt', import.meta.url),
      'utf-8'
    ).trim();

    expect(() => joinQRs([bad])).toThrow(/distance/);
  });

  test('reject invalid maxSize', () => {
    const v = doc.vectors[0];

    for (const bad of [NaN, 0, -1, 1.5, Infinity]) {
      expect(() => joinQRs(v.frames, bad)).toThrow(RangeError);
    }
  });

  test('cap decompressed size while inflating', () => {
    const v = doc.vectors.find((v: { name: string }) => v.name === 'deflate-psbt');

    // compressed input fits the cap; decompressed output must not
    expect(() => joinQRs(v.frames, v.input_length - 1)).toThrow(/too large/);
    expect(joinQRs(v.frames).raw.length).toBe(v.input_length);
  });
});
