import { useEffect, useState, type ImgHTMLAttributes } from 'react';
import { fileUrl } from 'src/service/files';

/** <img> dla chronionych plików API (plany, zdjęcia, logo). */
export default function AuthImage({ path, ...rest }: { path: string } & ImgHTMLAttributes<HTMLImageElement>) {
  const [src, setSrc] = useState<string>();
  useEffect(() => {
    let alive = true;
    fileUrl(path).then((u) => alive && setSrc(u)).catch(() => {});
    return () => {
      alive = false;
    };
  }, [path]);
  return src ? <img src={src} {...rest} /> : <img alt="" {...rest} style={{ ...rest.style, visibility: 'hidden' }} />;
}

export function useFileUrl(path: string | null) {
  const [src, setSrc] = useState<string>();
  useEffect(() => {
    if (!path) return;
    let alive = true;
    fileUrl(path).then((u) => alive && setSrc(u)).catch(() => {});
    return () => {
      alive = false;
    };
  }, [path]);
  return src;
}
