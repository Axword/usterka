import { rest } from './rest';

/** Pliki (plany, zdjęcia, logo) są chronione - pobieramy je z tokenem i trzymamy jako ObjectURL. */
const urlCache = new Map<string, Promise<string>>();
const imgCache = new Map<string, Promise<HTMLImageElement>>();

export function fileUrl(path: string): Promise<string> {
  let p = urlCache.get(path);
  if (!p) {
    p = rest.blob(path).then((b) => URL.createObjectURL(b));
    p.catch(() => urlCache.delete(path));
    urlCache.set(path, p);
  }
  return p;
}

export function fileImage(path: string): Promise<HTMLImageElement> {
  let p = imgCache.get(path);
  if (!p) {
    p = fileUrl(path).then(loadImg);
    p.catch(() => imgCache.delete(path));
    imgCache.set(path, p);
  }
  return p;
}

export async function fileBlob(path: string): Promise<Blob> {
  const u = await fileUrl(path);
  return (await fetch(u)).blob();
}

export function forgetFile(path: string) {
  const p = urlCache.get(path);
  urlCache.delete(path);
  imgCache.delete(path);
  p?.then((u) => URL.revokeObjectURL(u)).catch(() => {});
}

export function loadImg(src: string): Promise<HTMLImageElement> {
  return new Promise((res, rej) => {
    const i = new Image();
    i.onload = () => res(i);
    i.onerror = () => rej(new Error('Nie można odczytać obrazu'));
    i.src = src;
  });
}
