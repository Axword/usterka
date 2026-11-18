import { jsPDF } from 'jspdf';
import type { Project } from 'src/types/api';
import { fmtDate } from '../dates';
import { dueLabel, isFixed, typeLabel } from '../defects';
import { FONT_BOLD, FONT_REG } from './fonts';
import { fitBox, logoData, overviewData, prepareDefect, projectRows, type ImgData, type Progress, type ReportData, type ReportOptions } from './gather';

type RGB = [number, number, number];

export async function buildPDF(p: Project, data: ReportData, o: ReportOptions, prog: Progress): Promise<Blob> {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', compress: true });
  doc.addFileToVFS('Carlito-Regular.ttf', FONT_REG);
  doc.addFont('Carlito-Regular.ttf', 'Carlito', 'normal');
  doc.addFileToVFS('Carlito-Bold.ttf', FONT_BOLD);
  doc.addFont('Carlito-Bold.ttf', 'Carlito', 'bold');
  doc.setLineHeightFactor(1.3);
  const INK: RGB = [23, 32, 43];
  const MUTED: RGB = [91, 102, 114];
  const RED: RGB = [200, 16, 46];
  const GREEN: RGB = [30, 123, 74];
  const F = (st: 'normal' | 'bold' = 'normal', sz = 10, c: RGB = INK) => {
    doc.setFont('Carlito', st);
    doc.setFontSize(sz);
    doc.setTextColor(...c);
  };
  const LH = (sz: number) => sz * 0.3528 * 1.3;
  const M = 15;
  let PW = 210;
  let PH = 297;
  let y = M;
  const CW = () => PW - 2 * M;
  const bottom = () => PH - M - 6;
  const newPage = (or: 'p' | 'l' = 'p') => {
    doc.addPage('a4', or);
    PW = doc.internal.pageSize.getWidth();
    PH = doc.internal.pageSize.getHeight();
    y = M;
  };
  const room = (h: number) => y + h <= bottom();

  // nagłówek
  let logoH = 0;
  if (o.logo) {
    const L = await logoData(p);
    if (L) {
      const f = fitBox(L.w, L.h, 50, 20);
      doc.addImage(L.bytes, L.fmt, PW - M - f.w, M, f.w, f.h);
      logoH = f.h;
    }
  }
  const tw = CW() - (logoH ? 56 : 0);
  F('bold', 22);
  doc.text('Protokół usterek', M, y + 7);
  y += 13;
  F('bold', 14);
  const nl = doc.splitTextToSize(p.name, tw);
  doc.text(nl, M, y);
  y += nl.length * LH(14) + 1;
  F('normal', 10.5, MUTED);
  doc.text(`Data dokumentu: ${fmtDate(o.date)}`, M, y + 1);
  y = Math.max(y + 8, M + logoH + 6);

  // dane inwestycji
  doc.setDrawColor(205, 210, 203);
  doc.setLineWidth(0.25);
  doc.line(M, y, PW - M, y);
  for (const [k, v] of projectRows(p)) {
    F('normal', 10.5);
    const ls = doc.splitTextToSize(String(v || ''), CW() - 50);
    const h = ls.length * LH(10.5) + 3.6;
    F('bold', 10, MUTED);
    doc.text(k, M + 1, y + 5.2);
    F('normal', 10.5);
    doc.text(ls, M + 48, y + 5.2);
    y += h;
    doc.line(M, y, PW - M, y);
  }
  y += 9;

  // zestawienie
  const open = data.defects.filter((d) => !isFixed(d)).length;
  F('bold', 15);
  doc.text('Zestawienie usterek', M, y);
  y += 6;
  F('normal', 10.5, MUTED);
  doc.text(`Liczba usterek w protokole: ${data.defects.length} (otwarte: ${open}, usunięte: ${data.defects.length - open})`, M, y);
  y += 5;
  const cols: [string, number][] = [['Nr', 11], ['Rodzaj', 31], ['Opis', 66], ['Plan', 27], ['Termin', 25], ['Status', 20]];
  const head = () => {
    doc.setFillColor(232, 235, 230);
    doc.rect(M, y, CW(), 7.5, 'F');
    F('bold', 9.5);
    let x = M;
    for (const [t, w] of cols) {
      doc.text(t, x + 1.5, y + 5.1);
      x += w;
    }
    y += 7.5;
  };
  head();
  for (const d of data.defects) {
    F('normal', 9.5);
    const cells = [String(d.no), typeLabel(d), d.description, data.planMap.get(d.plan_id)!.name, dueLabel(d), isFixed(d) ? 'usunięta' : 'otwarta'].map(
      (t, i) => doc.splitTextToSize(String(t), cols[i][1] - 3) as string[],
    );
    const h = Math.max(...cells.map((c) => c.length)) * LH(9.5) + 3.2;
    if (!room(h)) {
      newPage('p');
      head();
    }
    let x = M;
    cells.forEach((c, i) => {
      F(i === 0 || i === 5 ? 'bold' : 'normal', 9.5, i === 5 ? (isFixed(d) ? GREEN : RED) : INK);
      doc.text(c, x + 1.5, y + 4.6);
      x += cols[i][1];
    });
    y += h;
    doc.setDrawColor(205, 210, 203);
    doc.line(M, y, PW - M, y);
  }

  // całe plany
  if (o.plans) {
    for (const pl of data.plans) {
      prog(`Przygotowanie planu ${pl.name}…`);
      const ov = await overviewData(pl, data);
      newPage(pl.width >= pl.height ? 'l' : 'p');
      F('bold', 15);
      doc.text((doc.splitTextToSize(`Plan: ${pl.name}`, CW()) as string[])[0], M, y + 5);
      F('normal', 9.5, MUTED);
      doc.setFillColor(...RED);
      doc.circle(PW - M - 52, y + 3.8, 1.6, 'F');
      doc.text('otwarta', PW - M - 49, y + 5);
      doc.setFillColor(...GREEN);
      doc.circle(PW - M - 30, y + 3.8, 1.6, 'F');
      doc.text('usunięta', PW - M - 27, y + 5);
      y += 10;
      const f = fitBox(ov.w, ov.h, CW(), bottom() - y);
      const x = M + (CW() - f.w) / 2;
      doc.addImage(ov.bytes, 'JPEG', x, y, f.w, f.h);
      doc.setDrawColor(150);
      doc.rect(x, y, f.w, f.h);
    }
  }

  // karty usterek
  newPage('p');
  F('bold', 17);
  doc.text('Karty usterek', M, y + 6);
  y += 14;
  const colW = 86;
  const gap = CW() - 2 * colW;
  const boxH = 60;
  for (let i = 0; i < data.defects.length; i++) {
    const d = data.defects[i];
    const R = await prepareDefect(d, data, prog, i);
    const fx = isFixed(d);
    const fields: [string, string][] = [['Rodzaj', typeLabel(d)], ['Plan', R.plan.name], ['Termin usunięcia', dueLabel(d)]];
    if (fx) fields.push(['Data usunięcia', fmtDate(d.fixed_date)]);
    fields.push(['Opis', d.description]);
    F('normal', 10.5);
    const fl = fields.map(([k, v]) => [k, doc.splitTextToSize(String(v || ''), colW - 2) as string[]] as const);
    const textH = fl.reduce((a, [, l]) => a + LH(9) + l.length * LH(10.5) + 2.2, 0);
    const cropH = colW * 0.75;
    const infoH = Math.max(textH, cropH);
    const firstPh = R.after.length || R.before.length ? 6 + boxH + 4 : 0;
    if (!room(12 + infoH + 7 + firstPh)) newPage('p');
    const bar = (cont: boolean) => {
      doc.setFillColor(...INK);
      doc.rect(M, y, CW(), 9, 'F');
      F('bold', 12, [255, 255, 255]);
      doc.text(`Usterka nr ${d.no}${cont ? ' (ciąg dalszy)' : ''}`, M + 3, y + 6.3);
      const st = fx ? 'USUNIĘTA' : 'OTWARTA';
      F('bold', 9.5, [255, 255, 255]);
      const sw = doc.getTextWidth(st) + 6;
      doc.setFillColor(...(fx ? GREEN : RED));
      doc.rect(PW - M - sw - 1.5, y + 1.5, sw, 6, 'F');
      doc.text(st, PW - M - sw + 1.5, y + 5.8);
      y += 12;
    };
    bar(false);
    let ty = y;
    for (const [k, l] of fl) {
      F('bold', 9, MUTED);
      doc.text(k, M, ty + 3);
      ty += LH(9);
      F('normal', 10.5);
      doc.text(l, M, ty + 3.4);
      ty += l.length * LH(10.5) + 2.2;
    }
    const cx = M + colW + gap;
    doc.addImage(R.crop.bytes, 'JPEG', cx, y, colW, cropH);
    doc.setDrawColor(150);
    doc.rect(cx, y, colW, cropH);
    F('normal', 8, MUTED);
    doc.text('Wycinek planu', cx, y + cropH + 3.5);
    y += infoH + 7;
    const photoRow = (imgs: (ImgData | undefined)[]) => {
      imgs.forEach((im, j) => {
        if (!im) return;
        const f = fitBox(im.w, im.h, colW, boxH);
        const bx = M + j * (colW + gap) + (colW - f.w) / 2;
        doc.addImage(im.bytes, im.fmt, bx, y, f.w, f.h);
        doc.setDrawColor(190);
        doc.rect(bx, y, f.w, f.h);
      });
      y += boxH + 4;
    };
    const heads = (a: string, b?: string) => {
      F('bold', 10);
      doc.text(a, M, y + 3.5);
      if (b) doc.text(b, M + colW + gap, y + 3.5);
      y += 6;
    };
    if (R.after.length) {
      const n = Math.max(R.before.length, R.after.length);
      if (!room(6 + boxH)) {
        newPage('p');
        bar(true);
      }
      heads('Przed usunięciem', 'Po usunięciu');
      for (let r = 0; r < n; r++) {
        if (!room(boxH)) {
          newPage('p');
          bar(true);
          heads('Przed usunięciem', 'Po usunięciu');
        }
        photoRow([R.before[r], R.after[r]]);
      }
    } else if (R.before.length) {
      if (!room(6 + boxH)) {
        newPage('p');
        bar(true);
      }
      heads('Zdjęcia usterki');
      for (let r = 0; r < R.before.length; r += 2) {
        if (!room(boxH)) {
          newPage('p');
          bar(true);
          heads('Zdjęcia usterki');
        }
        photoRow([R.before[r], R.before[r + 1]]);
      }
    }
    y += 4;
  }

  // podpisy
  if (!room(48)) newPage('p');
  y += 8;
  F('bold', 12);
  doc.text('Podpisy', M, y);
  y += 8;
  const sig: [string, string][] = [['Przedstawiciel Inwestora', p.investor], ['Przedstawiciel Wykonawcy', p.contractor]];
  sig.forEach(([l, n], j) => {
    const x = M + j * (colW + gap);
    F('bold', 10);
    doc.text(l, x, y);
    F('normal', 10, MUTED);
    doc.text(doc.splitTextToSize(n, colW), x, y + 5);
    doc.setDrawColor(120);
    doc.setLineDashPattern([0.8, 0.8], 0);
    doc.line(x, y + 26, x + colW, y + 26);
    doc.setLineDashPattern([], 0);
    F('normal', 8.5, MUTED);
    doc.text('data i podpis', x, y + 30);
  });
  y += 36;
  F('normal', 10, MUTED);
  doc.text(`Sporządził(a): ${p.author}`, M, y);

  // stopki
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i);
    const w = doc.internal.pageSize.getWidth();
    const h = doc.internal.pageSize.getHeight();
    F('normal', 8, [120, 126, 132]);
    doc.text((doc.splitTextToSize(`${p.name} – protokół usterek z dnia ${fmtDate(o.date)}`, w - 2 * M - 30) as string[])[0], M, h - 8);
    doc.text(`Strona ${i} z ${n}`, w - M, h - 8, { align: 'right' });
  }
  prog('Zapisywanie pliku…');
  return doc.output('blob');
}
