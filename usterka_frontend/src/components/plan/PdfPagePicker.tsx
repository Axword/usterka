import { useEffect, useRef } from 'react';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import Sheet from 'src/components/common/Sheet';
import { renderThumb } from 'src/utils/pdfImport';

interface Props {
  pdf: PDFDocumentProxy;
  onPick: (page: number | null) => void;
}

export default function PdfPagePicker({ pdf, onPick }: Props) {
  const refs = useRef<(HTMLCanvasElement | null)[]>([]);
  useEffect(() => {
    let alive = true;
    (async () => {
      for (let i = 0; i < pdf.numPages; i++) {
        if (!alive) return;
        const c = refs.current[i];
        if (c) await renderThumb(pdf, i + 1, c).catch(() => {});
      }
    })();
    return () => {
      alive = false;
    };
  }, [pdf]);
  return (
    <Sheet title="Wybierz stronę z planem" onClose={() => onPick(null)}>
      <p className="muted" style={{ marginTop: 0 }}>Liczba stron w pliku: {pdf.numPages}</p>
      <div className="pages">
        {Array.from({ length: pdf.numPages }, (_, i) => (
          <button key={i} className="pagebtn" onClick={() => onPick(i + 1)}>
            <canvas ref={(el) => { refs.current[i] = el; }} />
            Strona {i + 1}
          </button>
        ))}
      </div>
    </Sheet>
  );
}
