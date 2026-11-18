import { DefectService } from 'src/service/defect';
import { fileBlob, fileImage, loadImg } from 'src/service/files';
import { PlanService } from 'src/service/plan';
import { ProjectService } from 'src/service/project';
import type { Defect, DefectFilter, Plan, Project } from 'src/types/api';
import { fmtDate } from '../dates';
import { isFixed } from '../defects';
import { canvasToBlob, renderCrop, renderOverview, toPin } from '../images';

export interface ImgData {
  bytes: Uint8Array;
  w: number;
  h: number;
  fmt: 'PNG' | 'JPEG';
}

export interface ReportData {
  plans: Plan[];
  planMap: Map<string, Plan>;
  defects: Defect[];
}

export interface ReportOptions {
  date: string;
  filter: DefectFilter;
  plans: boolean;
  logo: boolean;
}

export type Progress = (t: string) => void;

export function selectDefects(plans: Plan[], defects: Defect[], filter: DefectFilter): ReportData {
  let ds = [...defects].sort((a, b) => a.no - b.no);
  if (filter === 'open') ds = ds.filter((d) => !isFixed(d));
  if (filter === 'fixed') ds = ds.filter(isFixed);
  return { plans: plans.filter((p) => ds.some((d) => d.plan_id === p.id)), planMap: new Map(plans.map((p) => [p.id, p])), defects: ds };
}

export async function blobData(blob: Blob): Promise<ImgData> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const u = URL.createObjectURL(blob);
  try {
    const i = await loadImg(u);
    return { bytes, w: i.naturalWidth, h: i.naturalHeight, fmt: /png/i.test(blob.type) ? 'PNG' : 'JPEG' };
  } finally {
    URL.revokeObjectURL(u);
  }
}

export async function canvasData(c: HTMLCanvasElement, q = 0.85): Promise<ImgData> {
  const b = await canvasToBlob(c, 'image/jpeg', q);
  const out: ImgData = { bytes: new Uint8Array(await b.arrayBuffer()), w: c.width, h: c.height, fmt: 'JPEG' };
  c.width = c.height = 0;
  return out;
}

export const fitBox = (w: number, h: number, bw: number, bh: number) => {
  const k = Math.min(bw / w, bh / h);
  return { w: w * k, h: h * k };
};

export const projectRows = (p: Project): [string, string][] => [
  ['Nazwa inwestycji', p.name],
  ['Adres inwestycji', p.address],
  ['Inwestor', p.investor],
  ['Wykonawca', p.contractor],
  ['Data przeglądu', fmtDate(p.inspection_date)],
  ['Sporządził(a)', p.author],
];

export const planImage = (plan: Plan) => fileImage(PlanService.imageUrl(plan.id));

export async function logoData(p: Project): Promise<ImgData | null> {
  if (!p.has_logo) return null;
  return blobData(await fileBlob(ProjectService.logoUrl(p.id)));
}

export async function overviewData(plan: Plan, data: ReportData) {
  const img = await planImage(plan);
  return canvasData(renderOverview(img, data.defects.filter((d) => d.plan_id === plan.id).map(toPin)), 0.85);
}

export async function prepareDefect(d: Defect, data: ReportData, prog: Progress, i: number) {
  prog(`Przygotowanie usterki ${i + 1} z ${data.defects.length}…`);
  const plan = data.planMap.get(d.plan_id)!;
  const img = await planImage(plan);
  const crop = await canvasData(renderCrop(img, toPin(d), data.defects.map(toPin), null, 1200, 900), 0.88);
  const load = async (kind: 'before' | 'after') => {
    const out: ImgData[] = [];
    for (const ph of d.photos.filter((p) => p.kind === kind)) out.push(await blobData(await fileBlob(DefectService.photoUrl(ph.id))));
    return out;
  };
  return { plan, crop, before: await load('before'), after: await load('after') };
}
