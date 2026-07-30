/**
 * (c) Copyright 2024 by Coinkite Inc. This file is in the public domain.
 *
 * QR code decoding/joining.
 */

import { DEFAULT_MAX_SIZE, ENCODINGS, HEADER_LEN } from './consts';
import { Encoding, JoinResult } from './types';
import { decodeData } from './utils';

// strict header grammar: B$ magic, known encoding, one uppercase letter of
// file type, then uppercase base-36 digits for part count and index
const HEADER_RE = /^B\$[H2Z][A-Z][0-9A-Z]{2}[0-9A-Z]{2}$/;

/**
 * Decodes and joins QR code parts back to binary data.
 *
 * @param parts Array of QR code parts
 * @param maxSize Cap on decoded/decompressed transfer size in bytes.
 * @returns Object containing the file type, encoding, and raw binary data.
 */
export function joinQRs(parts: string[], maxSize = DEFAULT_MAX_SIZE): JoinResult {
  for (const p of parts) {
    if (!HEADER_RE.test(p.slice(0, HEADER_LEN))) {
      throw new Error(`invalid header: ${p.slice(0, HEADER_LEN)}`);
    }

    if (p.length === HEADER_LEN) {
      throw new Error('empty body');
    }
  }

  const headers = new Set(parts.map((p) => p.slice(0, 6)));

  if (headers.size !== 1) {
    throw new Error('conflicting/variable filetype/encodings/sizes');
  }

  const header = [...headers][0];

  if (header.slice(0, 2) !== 'B$') {
    throw new Error('fixed header not found, expected B$');
  }

  if (!ENCODINGS.has(header[2])) {
    throw new Error(`bad encoding: ${header[2]}`);
  }

  const encoding = header[2] as Encoding;
  const fileType = header[3];

  if (!/^[A-Z]$/.test(fileType)) {
    throw new Error('fileType must be a single uppercase letter');
  }

  const numParts = parseInt(header.slice(4, 6), 36);

  if (numParts < 1) {
    throw new Error('zero parts?');
  }

  const data = new Map<number, string>();
  let bodyLen: number | null = null;

  for (const p of parts) {
    const idx = parseInt(p.slice(6, 8), 36);

    if (idx >= numParts) {
      throw new Error(`got part ${idx} but only expecting ${numParts}`);
    }

    if (data.has(idx) && data.get(idx) !== p.slice(8)) {
      throw new Error(`Duplicate part 0x${idx.toString(16)} has wrong content`);
    }

    data.set(idx, p.slice(8));

    if (idx !== numParts - 1) {
      // all non-final bodies must share one length
      bodyLen = bodyLen ?? p.length - HEADER_LEN;

      if (p.length - HEADER_LEN !== bodyLen) {
        throw new Error('non-final parts must have equal length');
      }
    }
  }

  const orderedParts = [];

  for (let i = 0; i < numParts; i++) {
    const p = data.get(i);

    if (!p) {
      throw new Error(`Part ${i} is missing`);
    }

    orderedParts.push(p);
  }

  if (numParts > 1 && orderedParts[numParts - 1].length > bodyLen!) {
    // final body must be no longer than the others
    throw new Error('final part too long');
  }

  const raw = decodeData(orderedParts, encoding, maxSize);

  if (!raw.length) {
    throw new Error('empty transfer');
  }

  return { fileType, encoding, raw };
}

// EOF
