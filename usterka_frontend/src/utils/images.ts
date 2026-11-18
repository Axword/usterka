import { COL, clamp } from './defects';
import { loadImg } from 'src/service/files';

export interface PinLike {
  id: string;
  plan_id: string;
  no: number | string;
  x: number;
  y: number;
  zoom: number;
  fixed: boolean;
}

export async function fileToImage(file: Blob): Promise<HTMLImageElement> {
  const u = URL.createObjectURL(file);
  try {
    return await loadImg(u);
  } finally {
    URL.revokeObjectURL(u);
  }
}

export function canvasToBlob(c: HTMLCanvasElement, type = 'image/jpeg', q = 0.85): Promise<Blob> {
  return new Promise((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error('Błąd przetwarzania obrazu'))), type, q));
}

/** Skalowanie przed wysłaniem: mniejszy transfer na budowie (LTE). */
export async function resizeImage(img: HTMLImageElement, maxSide: number, q: number, type = 'image/jpeg', maxArea = 12e6) {
  const w = img.naturalWidth;
  const h = img.naturalHeight;
  let k = Math.min(1, maxSide / Math.max(w, h));
  if (w * h * k * k > maxArea) k = Math.sqrt(maxArea / (w * h));
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(w * k));
  c.height = Math.max(1, Math.round(h * k));
  const x = c.getContext('2d')!;
  if (type === 'image/jpeg') {
    x.fillStyle = '#fff';
    x.fillRect(0, 0, c.width, c.height);
  }
  x.drawImage(img, 0, 0, c.width, c.height);
  const blob = await canvasToBlob(c, type, q);
  const out = { blob, w: c.width, h: c.height };
  c.width = c.height = 0;
  return out;
}

export function drawPin(ctx: CanvasRenderingContext2D, x: number, y: number, r: number, no: number | string, fixed: boolean, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  const cy = y - r * 1.75;
  const path = () => {
    ctx.beginPath();
    ctx.arc(x, cy, r, 0, Math.PI * 2);
    ctx.moveTo(x - r * 0.55, cy + r * 0.83);
    ctx.lineTo(x, y);
    ctx.lineTo(x + r * 0.55, cy + r * 0.83);
    ctx.closePath();
  };
  path();
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = r * 0.34;
  ctx.lineJoin = 'round';
  ctx.stroke();
  path();
  ctx.fillStyle = fixed ? COL.fixed : COL.open;
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.font = `700 ${Math.round(r * (String(no).length > 2 ? 0.95 : 1.2))}px "Barlow Condensed", Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(String(no), x, cy + r * 0.06);
  ctx.restore();
}

/** Wycinek planu wokół usterki; zoom = szerokość wycinka jako ułamek dłuższego boku planu. */
export function renderCrop(img: HTMLImageElement, d: PinLike, others: PinLike[], canvas?: HTMLCanvasElement | null, W = 1200, H = 900) {
  const iw = img.naturalWidth;
  const ih = img.naturalHeight;
  const L = Math.max(iw, ih);
  let cw = (d.zoom || 0.3) * L;
  let ch = (cw * H) / W;
  if (cw > iw) {
    cw = iw;
    ch = (cw * H) / W;
  }
  if (ch > ih) {
    ch = ih;
    cw = (ch * W) / H;
  }
  const px = d.x * iw;
  const py = d.y * ih;
  const sx = clamp(px - cw / 2, 0, iw - cw);
  const sy = clamp(py - ch / 2, 0, ih - ch);
  const c = canvas || document.createElement('canvas');
  c.width = W;
  c.height = H;
  const x = c.getContext('2d')!;
  x.fillStyle = '#fff';
  x.fillRect(0, 0, W, H);
  x.imageSmoothingQuality = 'high';
  x.drawImage(img, sx, sy, cw, ch, 0, 0, W, H);
  const k = W / cw;
  const r = W * 0.034;
  for (const o of others) {
    if (o.id === d.id || o.plan_id !== d.plan_id) continue;
    const ox = (o.x * iw - sx) * k;
    const oy = (o.y * ih - sy) * k;
    if (ox < -r || oy < -r || ox > W + r || oy > H + 3 * r) continue;
    drawPin(x, ox, oy, r * 0.75, o.no, o.fixed, 0.55);
  }
  const tx = (px - sx) * k;
  const ty = (py - sy) * k;
  x.strokeStyle = d.fixed ? COL.fixed : COL.open;
  x.lineWidth = W * 0.006;
  x.beginPath();
  x.arc(tx, ty, W * 0.045, 0, Math.PI * 2);
  x.stroke();
  drawPin(x, tx, ty, r, d.no ?? '?', d.fixed);
  x.strokeStyle = 'rgba(0,0,0,.35)';
  x.lineWidth = 2;
  x.strokeRect(1, 1, W - 2, H - 2);
  return c;
}

export function renderOverview(img: HTMLImageElement, pins: PinLike[]) {
  const c = document.createElement('canvas');
  const iw = img.naturalWidth;
  const ih = img.naturalHeight;
  c.width = iw;
  c.height = ih;
  const x = c.getContext('2d')!;
  x.fillStyle = '#fff';
  x.fillRect(0, 0, iw, ih);
  x.drawImage(img, 0, 0);
  const r = Math.max(14, Math.max(iw, ih) * 0.011);
  for (const d of [...pins].sort((a, b) => a.y - b.y)) drawPin(x, d.x * iw, d.y * ih, r, d.no, d.fixed);
  return c;
}

export const toPin = (d: { id: string; plan_id: string; no: number | null; x: number; y: number; zoom: number; status?: string }): PinLike => ({
  id: d.id,
  plan_id: d.plan_id,
  no: d.no ?? '?',
  x: d.x,
  y: d.y,
  zoom: d.zoom,
  fixed: d.status === 'fixed',
});
