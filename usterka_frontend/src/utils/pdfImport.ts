import type { PDFDocumentProxy } from 'pdfjs-dist';
import { canvasToBlob } from './images';

/** pdf.js ładowany leniwie i z lokalnego bundla (działa offline, bez CDN). */
async function pdfjs() {
  const lib = await import('pdfjs-dist');
  const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url');
  lib.GlobalWorkerOptions.workerSrc = worker.default;
  return lib;
}

export async function openPdf(file: Blob): Promise<PDFDocumentProxy> {
  const lib = await pdfjs();
  return lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()), isEvalSupported: false }).promise;
}

/** Strona PDF -> JPEG (dłuższy bok ~3500 px, maks. 13 MPx). */
export async function renderPdfPage(pdf: PDFDocumentProxy, n: number) {
  const page = await pdf.getPage(n);
  const v1 = page.getViewport({ scale: 1 });
  let scale = 3500 / Math.max(v1.width, v1.height);
  const area = v1.width * v1.height * scale * scale;
  if (area > 13e6) scale *= Math.sqrt(13e6 / area);
  const vp = page.getViewport({ scale });
  const c = document.createElement('canvas');
  c.width = Math.floor(vp.width);
  c.height = Math.floor(vp.height);
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, c.width, c.height);
  await page.render({ canvasContext: ctx, viewport: vp }).promise;
  const blob = await canvasToBlob(c, 'image/jpeg', 0.9);
  const out = { blob, w: c.width, h: c.height };
  c.width = c.height = 0;
  return out;
}

export async function renderThumb(pdf: PDFDocumentProxy, n: number, canvas: HTMLCanvasElement) {
  const pg = await pdf.getPage(n);
  const v = pg.getViewport({ scale: 1 });
  const vp = pg.getViewport({ scale: 280 / Math.max(v.width, v.height) });
  canvas.width = vp.width;
  canvas.height = vp.height;
  await pg.render({ canvasContext: canvas.getContext('2d')!, viewport: vp }).promise;
}
