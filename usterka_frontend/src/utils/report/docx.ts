import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun, Packer, PageNumber, PageOrientation, Paragraph,
  ShadingType, Table, TableCell, TableRow, TextRun, VerticalAlign, WidthType,
  type IParagraphOptions, type IRunOptions, type ISectionOptions, type ITableCellOptions,
} from 'docx';
import type { Project } from 'src/types/api';
import { fmtDate } from '../dates';
import { dueLabel, isFixed, typeLabel } from '../defects';
import { fitBox, logoData, overviewData, prepareDefect, projectRows, type ImgData, type Progress, type ReportData, type ReportOptions } from './gather';

type RunX = Omit<IRunOptions, 'text'>;

export async function buildDOCX(p: Project, data: ReportData, o: ReportOptions, prog: Progress): Promise<Blob> {
  const PX = 96 / 25.4;
  const FULL = 10206;
  const HALF = 5103;
  const R = (t: unknown, x: RunX = {}) => new TextRun({ text: String(t ?? ''), ...x });
  const ML = (t: unknown, x: RunX = {}) => String(t ?? '').split('\n').map((l, i) => new TextRun({ text: l, break: i ? 1 : 0, ...x }));
  const P = (ch: TextRun | ImageRun | (TextRun | ImageRun)[] | string, x: Omit<IParagraphOptions, 'children'> = {}) =>
    typeof ch === 'string' ? new Paragraph({ text: ch, ...x }) : new Paragraph({ children: Array.isArray(ch) ? ch : [ch], ...x });
  const IMG = (im: ImgData, wmm: number, hmm: number) =>
    new ImageRun({ type: im.fmt === 'PNG' ? 'png' : 'jpg', data: im.bytes, transformation: { width: Math.round(wmm * PX), height: Math.round(hmm * PX) } });
  const NB = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  const NOB = { top: NB, bottom: NB, left: NB, right: NB };
  const LB = { style: BorderStyle.SINGLE, size: 4, color: 'CDD2CB' };
  const LBS = { top: LB, bottom: LB, left: LB, right: LB };
  const C = (children: (Paragraph | Table)[], w: number, x: Partial<ITableCellOptions> = {}) =>
    new TableCell({ children, width: { size: w, type: WidthType.DXA }, margins: { top: 70, bottom: 70, left: 110, right: 110 }, borders: LBS, ...x });
  const page = (orientation: (typeof PageOrientation)[keyof typeof PageOrientation]) => ({
    page: { size: { width: 11906, height: 16838, orientation }, margin: { top: 850, bottom: 850, left: 850, right: 850, footer: 400 } },
  });
  const grey = { color: '5B6672' };
  const head = { shading: { type: ShadingType.CLEAR, color: 'auto', fill: 'E8EBE6' } };
  const footer = new Footer({
    children: [
      P(
        [
          R(`${p.name} – protokół usterek z dnia ${fmtDate(o.date)}     Strona `, { size: 16, ...grey }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, ...grey }),
          R(' z ', { size: 16, ...grey }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, ...grey }),
        ],
        { alignment: AlignmentType.RIGHT },
      ),
    ],
  });

  const s1: (Paragraph | Table)[] = [];
  if (o.logo) {
    const L = await logoData(p);
    if (L) {
      const f = fitBox(L.w, L.h, 50, 20);
      s1.push(P(IMG(L, f.w, f.h), { alignment: AlignmentType.RIGHT }));
    }
  }
  s1.push(P(R('Protokół usterek'), { heading: HeadingLevel.TITLE }));
  s1.push(P(R(p.name, { bold: true, size: 28 })));
  s1.push(P(R(`Data dokumentu: ${fmtDate(o.date)}`, grey), { spacing: { after: 240 } }));
  s1.push(
    new Table({
      width: { size: FULL, type: WidthType.DXA },
      columnWidths: [2900, FULL - 2900],
      rows: projectRows(p).map(([k, v]) => new TableRow({ children: [C([P(R(k, { bold: true, ...grey }))], 2900), C([P(ML(v))], FULL - 2900)] })),
    }),
  );
  const open = data.defects.filter((d) => !isFixed(d)).length;
  s1.push(P(R('Zestawienie usterek'), { heading: HeadingLevel.HEADING_1 }));
  s1.push(P(R(`Liczba usterek w protokole: ${data.defects.length} (otwarte: ${open}, usunięte: ${data.defects.length - open})`, grey), { spacing: { after: 120 } }));
  const cw = [620, 1750, 3700, 1520, 1400, 1216];
  const hd = ['Nr', 'Rodzaj', 'Opis', 'Plan', 'Termin', 'Status'];
  s1.push(
    new Table({
      width: { size: FULL, type: WidthType.DXA },
      columnWidths: cw,
      rows: [
        new TableRow({ tableHeader: true, children: hd.map((h, i) => C([P(R(h, { bold: true, size: 19 }))], cw[i], head)) }),
        ...data.defects.map(
          (d) =>
            new TableRow({
              cantSplit: true,
              children: (
                [
                  [String(d.no), { bold: true }],
                  [typeLabel(d)],
                  [d.description],
                  [data.planMap.get(d.plan_id)!.name],
                  [dueLabel(d)],
                  [isFixed(d) ? 'usunięta' : 'otwarta', { bold: true, color: isFixed(d) ? '1E7B4A' : 'C8102E' }],
                ] as [string, RunX?][]
              ).map(([t, x], i) => C([P(ML(t, { size: 19, ...(x || {}) }))], cw[i])),
            }),
        ),
      ],
    }),
  );
  const sections: ISectionOptions[] = [{ properties: page(PageOrientation.PORTRAIT), footers: { default: footer }, children: s1 }];

  if (o.plans) {
    for (const pl of data.plans) {
      prog(`Przygotowanie planu ${pl.name}…`);
      const ov = await overviewData(pl, data);
      const land = pl.width >= pl.height;
      const f = fitBox(ov.w, ov.h, land ? 267 : 180, land ? 160 : 245);
      sections.push({
        properties: page(land ? PageOrientation.LANDSCAPE : PageOrientation.PORTRAIT),
        footers: { default: footer },
        children: [
          P(R(`Plan: ${pl.name}`), { heading: HeadingLevel.HEADING_1 }),
          P([R('● ', { color: 'C8102E' }), R('otwarta    ', grey), R('● ', { color: '1E7B4A' }), R('usunięta', grey)]),
          P(IMG(ov, f.w, f.h), { alignment: AlignmentType.CENTER }),
        ],
      });
    }
  }

  const s3: (Paragraph | Table)[] = [P(R('Karty usterek'), { heading: HeadingLevel.HEADING_1 })];
  const cellImg = (im?: ImgData) => {
    if (!im) return [P('')];
    const f = fitBox(im.w, im.h, 84, 60);
    return [P(IMG(im, f.w, f.h), { alignment: AlignmentType.CENTER })];
  };
  for (let i = 0; i < data.defects.length; i++) {
    const d = data.defects[i];
    const Rr = await prepareDefect(d, data, prog, i);
    const fx = isFixed(d);
    s3.push(P([R(`Usterka nr ${d.no}  `), R(fx ? 'usunięta' : 'otwarta', { color: fx ? '1E7B4A' : 'C8102E' })], { heading: HeadingLevel.HEADING_2, keepNext: true }));
    const fields: [string, string][] = [['Rodzaj', typeLabel(d)], ['Plan', Rr.plan.name], ['Termin usunięcia', dueLabel(d)]];
    if (fx) fields.push(['Data usunięcia', fmtDate(d.fixed_date)]);
    fields.push(['Opis', d.description]);
    const info = fields.flatMap(([k, v]) => [P(R(k, { bold: true, size: 18, ...grey }), { spacing: { before: 80 } }), P(ML(v))]);
    s3.push(
      new Table({
        width: { size: FULL, type: WidthType.DXA },
        columnWidths: [HALF, HALF],
        rows: [
          new TableRow({
            cantSplit: true,
            children: [C(info, HALF, { borders: NOB }), C([P(IMG(Rr.crop, 84, 63)), P(R('Wycinek planu', { size: 16, ...grey }))], HALF, { borders: NOB })],
          }),
        ],
      }),
    );
    const row = (a?: ImgData, b?: ImgData) =>
      new TableRow({ cantSplit: true, children: [C(cellImg(a), HALF, { verticalAlign: VerticalAlign.CENTER }), C(cellImg(b), HALF, { verticalAlign: VerticalAlign.CENTER })] });
    if (Rr.after.length) {
      const n = Math.max(Rr.before.length, Rr.after.length);
      const rows = [new TableRow({ tableHeader: true, children: [C([P(R('Przed usunięciem', { bold: true }))], HALF, head), C([P(R('Po usunięciu', { bold: true }))], HALF, head)] })];
      for (let r = 0; r < n; r++) rows.push(row(Rr.before[r], Rr.after[r]));
      s3.push(P(''));
      s3.push(new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [HALF, HALF], rows }));
    } else if (Rr.before.length) {
      const rows = [new TableRow({ tableHeader: true, children: [C([P(R('Zdjęcia usterki', { bold: true }))], FULL, { columnSpan: 2, ...head })] })];
      for (let r = 0; r < Rr.before.length; r += 2) rows.push(row(Rr.before[r], Rr.before[r + 1]));
      s3.push(P(''));
      s3.push(new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [HALF, HALF], rows }));
    }
    s3.push(P('', { spacing: { after: 240 } }));
  }
  s3.push(P(R('Podpisy'), { heading: HeadingLevel.HEADING_1, keepNext: true }));
  const sigCell = (l: string, n: string) =>
    C(
      [
        P(R(l, { bold: true }), { keepNext: true }),
        P(R(n, grey), { keepNext: true }),
        P('', { spacing: { before: 600 }, keepNext: true }),
        P(R('.................................................................'), { keepNext: true }),
        P(R('data i podpis', { size: 16, ...grey })),
      ],
      HALF,
      { borders: NOB },
    );
  s3.push(
    new Table({
      width: { size: FULL, type: WidthType.DXA },
      columnWidths: [HALF, HALF],
      rows: [new TableRow({ cantSplit: true, children: [sigCell('Przedstawiciel Inwestora', p.investor), sigCell('Przedstawiciel Wykonawcy', p.contractor)] })],
    }),
  );
  s3.push(P(R(`Sporządził(a): ${p.author}`, grey), { spacing: { before: 240 } }));
  sections.push({ properties: page(PageOrientation.PORTRAIT), footers: { default: footer }, children: s3 });

  const doc = new Document({
    creator: p.author,
    title: `Protokół usterek – ${p.name}`,
    styles: {
      default: { document: { run: { font: 'Calibri', size: 21 } } },
      paragraphStyles: [
        { id: 'Title', name: 'Title', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 44, bold: true, color: '17202B' }, paragraph: { spacing: { after: 120 } } },
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 30, bold: true, color: '17202B' }, paragraph: { spacing: { before: 360, after: 120 }, keepNext: true } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 26, bold: true, color: '17202B' }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true } },
      ],
    },
    sections,
  });
  prog('Zapisywanie pliku…');
  return Packer.toBlob(doc);
}
