import QRCode from 'qrcode';
import { expect, test } from 'vitest';
import { HEADER_LEN, QR_DATA_CAPACITY } from '../src/consts';
import { joinQRs } from '../src/join';
import { splitQRs } from '../src/split';
import { Encoding, FileType, Version } from '../src/types';
import { shuffled } from '../src/utils';

// helper to create cartesian product of arrays akin to @pytest.mark.parametrize over multiple parameters
// https://stackoverflow.com/a/43053803
function cartesian(...a: any[][]) {
  return a.reduce((a, b) => a.flatMap((d) => b.map((e) => [d, e].flat())));
}

// for validating QRs
function producesValidQRs(parts: string[], version: number) {
  try {
    for (const p of parts) {
      QRCode.create([{ data: p, mode: 'alphanumeric' }], {
        version,
        errorCorrectionLevel: 'L',
      });
    }

    return true;
  } catch (err) {
    return false;
  }
}

const LOOPBACK_CASES: [Encoding | undefined, number, Version, boolean, FileType][] = cartesian(
  [undefined, 'H', '2', 'Z'], // encoding
  [10, 100, 2000, 10_000, 50_000], // size
  [11, 29, 40], // maxVersion
  [true, false], // lowEntropy
  ['P', 'T'] // fileType
);

test('Loopback', () => {
  for (const [i, tc] of LOOPBACK_CASES.entries()) {
    const [encoding, size, maxVersion, lowEntropy, fileType] = tc;

    const data = new Uint8Array(size);
    if (lowEntropy) {
      data.fill(0x41);
    } else {
      crypto.getRandomValues(data);
    }

    const { version, parts } = splitQRs(data, fileType, { encoding, maxVersion });

    expect(version).toBeLessThanOrEqual(maxVersion);

    if (encoding && encoding !== parts[0][2]) {
      // encoding can only change from 'Z' to '2' if Zlib doesn't provide a smaller result
      expect(encoding).toBe('Z');
      expect(parts[0][2]).toBe('2');
    }

    const decoded = joinQRs(parts);
    expect(decoded.fileType).toBe(fileType);
    expect(decoded.raw).toEqual(data);

    const randomized = shuffled(parts);
    const decoded2 = joinQRs(randomized);
    expect(decoded2.fileType).toBe(fileType);
    expect(decoded2.raw).toEqual(data);

    // try to construct a few QRs. too slow to do for every case
    if (i % 50 === 0) {
      expect(producesValidQRs(parts, version)).toBe(true);
    }
  }
}, 10_000);

test('Minimum split', () => {
  const data = new Uint8Array(10_000);
  crypto.getRandomValues(data);

  for (let i = 2; i < 10; i++) {
    const { parts, version } = splitQRs(data, 'T', { encoding: '2', minSplit: i });

    expect(parts.length).toBeGreaterThanOrEqual(i);

    const decoded = joinQRs(parts);

    expect(decoded.fileType).toBe('T');
    expect(decoded.raw).toEqual(data);

    expect(producesValidQRs(parts, version)).toBe(true);
  }
});

const V27_EDGE_CASES: [Encoding, number, boolean][] = cartesian(
  ['H', '2', 'Z'], // encoding
  Array.from({ length: 20 }, (_, i) => i + 1060), // size
  [true, false] // lowEntropy
);

test('Version 27 edge cases', () => {
  for (const c of V27_EDGE_CASES) {
    const [encoding, size, lowEntropy] = c;

    const needVersion = 27;

    const data = new Uint8Array(size);
    if (lowEntropy) {
      data.fill(0x41);
    } else {
      crypto.getRandomValues(data);
    }

    const { parts, version: actualVersion } = splitQRs(data, 'T', {
      encoding,
      maxSplit: 2,
      minVersion: needVersion,
      maxVersion: needVersion,
    });

    expect(actualVersion).toBe(needVersion);

    if (encoding === 'H') {
      expect(parts.length).toBe(size <= 1062 ? 1 : 2);
    } else if (encoding === 'Z') {
      expect(parts.length).toBe(1);
      if (lowEntropy) {
        expect(parts[0].length).toBeLessThan(100);
      }
    } else if (encoding === '2') {
      expect(parts.length).toBe(1);
    }

    const decoded = joinQRs(parts);

    expect(decoded.fileType).toBe('T');
    expect(decoded.raw).toEqual(data);
  }
});

test.each(['H', '2'] as const)(`Test max size for encoding %s`, (encoding) => {
  const capacity = QR_DATA_CAPACITY[40]['L'][2] - HEADER_LEN;

  let pktSize: number;

  if (encoding === 'H') {
    pktSize = Math.floor(capacity / 2);
  } else if (encoding === '2') {
    pktSize = Math.floor((capacity * 5) / 8);
  } else {
    throw new Error('unreachable');
  }

  const nparts = 1295;

  const data = new Uint8Array(pktSize * nparts);

  // cannot use crypto.getRandomValues(data) - exceeds max size

  for (let i = 0; i < data.length; i++) {
    data[i] = Math.floor(Math.random() * 256);
  }

  const { parts, version } = splitQRs(data, 'T', { encoding, minVersion: 40 });

  expect(version).toBe(40);

  expect(parts.length).toBe(nparts);

  const decoded = joinQRs(parts);
  expect(decoded.raw).toEqual(data);

  // test a random part
  const idx = Math.floor(Math.random() * parts.length);
  expect(producesValidQRs([parts[idx]], version)).toBe(true);
}, 10_000);
