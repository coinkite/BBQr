import fs from 'fs';
import path from 'path';
import { expect, test } from 'vitest';
import { joinQRs } from '../src/join';

test('Test real-scan.txt', async () => {
  const lines = (
    await fs.promises.readFile(path.join(__dirname, '../../test_data/real-scan.txt'), 'utf-8')
  )
    .split('\n')
    .filter((l) => l.trim() !== '');

  const { fileType, raw } = joinQRs(lines);

  expect(fileType).toBe('U');

  const decoded = new TextDecoder().decode(raw);

  expect(decoded).toContain('Zlib compressed');
  expect(decoded).toContain('PSBT');
});
