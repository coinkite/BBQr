/**
 * (c) Copyright 2024 by Coinkite Inc. This file is in the public domain.
 *
 * QR code image rendering.
 */

import QRCode from 'qrcode';
import UPNG from 'upng-js';
import { ImageOptions, Version } from './types';
import { shuffled } from './utils';

/**
 * Generates QR code images from the given parts and renders them as (animated) PNG.
 *
 * @param parts The string parts to encode as QR codes.
 * @param version The QR code version to use.
 * @param options An optional ImageOptions object.
 * @returns A Promise that resolves to an ArrayBuffer containing the image data;
 */
export async function renderQRImage(
  parts: string[],
  version: Version,
  options: ImageOptions = {}
): Promise<ArrayBuffer> {
  if (typeof window === 'undefined') {
    throw new Error('renderQRImage is only available in a web browser environment.');
  }

  const mode = options.mode ?? 'animated';

  const margin = 4;
  const scale = options.scale ?? 4;

  if (scale < 1) {
    throw new Error('scale cannot be less than 1');
  }

  let width = 0;
  let height = 0;

  const qrImages: HTMLImageElement[] = [];

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];

    const dataURL = await QRCode.toDataURL([{ data: part, mode: 'alphanumeric' }], {
      errorCorrectionLevel: 'L',
      version,
      margin,
      scale,
    });

    // Create an image and draw it onto the canvas to get its dimensions
    const img = new Image();
    img.src = dataURL;
    await img.decode();

    if (i === 0) {
      width = img.width;
      height = img.height;
    } else if (img.width !== width) {
      throw new Error('QR codes must all be the same size');
    }

    qrImages.push(img);
  }

  if (mode === 'stacked') {
    const spacing = width / 1.5;
    const totalHeight = height * parts.length + spacing * (parts.length - 1);

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      throw new Error('Could not get 2d context for canvas element.');
    }

    canvas.width = width;
    canvas.height = totalHeight;

    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, width, totalHeight);

    for (let i = 0; i < qrImages.length; i++) {
      const y = i * (height + spacing);
      ctx.drawImage(qrImages[i], 0, y);

      // Draw down arrow between QR codes (except after the last one)
      if (i < qrImages.length - 1) {
        const arrowY = y + height + spacing / 2;
        const arrowSize = width / 6;
        const arrowWidth = arrowSize * 2;
        const centerX = width / 2;

        // Draw arrow with low opacity
        ctx.save();
        ctx.globalAlpha = 0.05;
        ctx.beginPath();
        ctx.moveTo(centerX, arrowY + arrowSize / 2);
        ctx.lineTo(centerX + arrowWidth / 2, arrowY - arrowSize / 2);
        ctx.lineTo(centerX - arrowWidth / 2, arrowY - arrowSize / 2);
        ctx.closePath();
        ctx.fillStyle = '#000';
        ctx.fill();
        ctx.restore();
      }
    }

    const imgData = ctx.getImageData(0, 0, width, totalHeight).data;
    return UPNG.encode([imgData.buffer], width, totalHeight, 0);
  } else {
    const progressAreaHeight = parts.length > 1 ? 2 * scale : 0;

    const frames: ArrayBuffer[] = [];

    for (let i = 0; i < qrImages.length; i++) {
      if (i === 0) {
        height += progressAreaHeight;
      }

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        throw new Error('Could not get 2d context for canvas element.');
      }

      const img = qrImages[i];

      canvas.width = img.width;
      canvas.height = img.height + progressAreaHeight;

      ctx.drawImage(img, 0, 0);

      if (progressAreaHeight > 0) {
        // fill area between QR and progress bar
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, img.height, canvas.width, progressAreaHeight);

        // leave margin on sides of progress bar, so it's same width as the actual QR code
        const marginPixels = margin * scale;

        // but also a little bit of white space below the progress bar
        const progressBarHeight = progressAreaHeight / 2;

        const segmentWidth = (canvas.width - 2 * marginPixels) / parts.length;

        ctx.fillStyle = '#ccc';
        ctx.fillRect(marginPixels, img.height, canvas.width - 2 * marginPixels, progressBarHeight);

        ctx.fillStyle = '#000';
        ctx.fillRect(marginPixels + segmentWidth * i, img.height, segmentWidth, progressBarHeight);
      }
      const imgData = ctx.getImageData(0, 0, width, canvas.height).data;
      frames.push(imgData.buffer);
    }

    return UPNG.encode(
      options.randomizeOrder ? shuffled(frames) : frames,
      width,
      height,
      0,
      parts.map(() => options.frameDelay ?? 250)
    );
  }
}

// EOF
