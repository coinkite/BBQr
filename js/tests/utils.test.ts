import fs from 'fs';
import path from 'path';
import { expect, test } from 'vitest';
import { base64ToBytes, decodeData, encodeData, hexToBytes, intToBase36 } from '../src/utils';

test('Decode hex string to bytes', () => {
  const hex = '48656c6c6f20776f726c64'; // "Hello world"
  const expected = new Uint8Array([72, 101, 108, 108, 111, 32, 119, 111, 114, 108, 100]);

  expect(hexToBytes(hex)).toEqual(expected);
});

test('Decode base64 to binary', () => {
  const b64 = 'SGVsbG8gd29ybGQ='; // "Hello world"
  const expected = new Uint8Array([72, 101, 108, 108, 111, 32, 119, 111, 114, 108, 100]);

  expect(base64ToBytes(b64)).toEqual(expected);
});

test('Encode integers 0 thru 1295 to base32', () => {
  for (let i = 0; i <= 1295; i++) {
    const s = intToBase36(i);

    expect(s).toHaveLength(2);
    expect(s.toUpperCase()).toBe(s);

    expect(parseInt(s, 36)).toBe(i);
  }

  expect(() => intToBase36(-1)).toThrowError();
  expect(() => intToBase36(1296)).toThrowError();
});

const dataFiles = [
  '1in1000out.psbt',
  '1in100out.psbt',
  '1in10out.psbt',
  '1in20out.psbt',
  '1in2out.psbt',
  'devils-txn.txn',
  'finalized-by-ckcc.txn',
  'last.txn',
  'nfc-result.txn',
  'signed.txn',
];

test.each(dataFiles)('Encode, decode, measure Zlib compression: %s', async (file) => {
  // need the conversion to Uint8Array because node's Buffer won't be equal
  const raw = new Uint8Array(
    await fs.promises.readFile(path.join(__dirname, '../../test_data', file))
  );

  const { encoded, encoding } = encodeData(raw, 'Z');

  expect(encoding).toBe('Z');

  const decoded = decodeData([encoded], 'Z');

  expect(decoded).toEqual(raw);

  // decode with base32 only and see how much smaller it is
  const decodedCompressed = decodeData([encoded], '2');

  expect(decodedCompressed.length).toBeLessThan(raw.length);

  const ratio = 100 - (decodedCompressed.length * 100) / raw.length;

  console.log(
    `${file}: ${raw.length} => ${decodedCompressed.length}, ${ratio.toFixed(1)}% compression`
  );
});
