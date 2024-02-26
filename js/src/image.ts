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
 * @param options.frameDelay The delay between frames in the animated PNG in milliseconds. Defaults to 250.
 * @param options.randomizeOrder Whether to randomize the order of the parts. Defaults to false.
 * @returns A Promise that resolves to an ArrayBuffer containing the image data;
 */
export async function renderQRImage(
  parts: string[],
  version: Version,
  options: ImageOptions = {}
): Promise<ArrayBuffer> {
  if (typeof window === 'undefined') {
    throw new Error('makeImage is only available in a web browser environment.');
  }

  const frameDelay = options.frameDelay ?? 250;

  if (options.randomizeOrder) {
    parts = shuffled(parts);
  }

  const frames: ArrayBuffer[] = [];

  let width = 0;
  let height = 0;

  // additional space for progress bar, if more than one part
  const progressAreaHeight = parts.length > 1 ? 20 : 0;

  // quiet zone
  const margin = 4;

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];

    const dataURL = await QRCode.toDataURL([{ data: part, mode: 'alphanumeric' }], {
      errorCorrectionLevel: 'L',
      version,
      margin,
    });

    // Create an image and draw it onto the canvas to get its dimensions
    const img = new Image();
    img.src = dataURL;
    await img.decode();

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      throw new Error('Could not get 2d context for canvas element.');
    }

    canvas.width = img.width;
    canvas.height = img.height + progressAreaHeight;

    ctx.drawImage(img, 0, 0);

    if (progressAreaHeight > 0) {
      // fill area between QR and progress bar
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, img.height, canvas.width, progressAreaHeight);

      const progressBarHeight = progressAreaHeight / 4;
      const progressBarY = img.height + progressAreaHeight / 2; // Position the progress bar below the QR code
      const segmentWidth = canvas.width / parts.length;

      ctx.fillStyle = '#ccc';
      ctx.fillRect(0, progressBarY, canvas.width, progressBarHeight);

      ctx.fillStyle = '#000';

      ctx.fillRect(segmentWidth * i, progressBarY, segmentWidth, progressBarHeight);
    }

    if (i === 0) {
      width = canvas.width;
      height = canvas.height;
    } else if (canvas.width !== width || canvas.height !== height) {
      throw new Error('QR codes must all be the same size');
    }

    const imgData = ctx.getImageData(0, 0, width, height).data;
    frames.push(imgData.buffer);
  }

  const delays = parts.map(() => frameDelay);

  return UPNG.encode(frames, width, height, 0, delays);
}
