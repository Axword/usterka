import type { Defect } from 'src/types/api';
import { fmtDate } from './dates';

export const COL = { open: '#C8102E', fixed: '#1E7B4A' };
export const isFixed = (d: Pick<Defect, 'status'>) => d.status === 'fixed';
export const typeLabel = (d: Pick<Defect, 'type' | 'type_other'>) =>
  d.type === 'Inna' && d.type_other ? `Inna (${d.type_other})` : d.type;
export const dueLabel = (d: Pick<Defect, 'due_mode' | 'due_date'>) =>
  d.due_mode === 'umowa' ? 'Zgodnie z umową' : fmtDate(d.due_date);
export const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
export const safeName = (s: string) =>
  String(s).replace(/[\\/:*?"<>|]+/g, '').replace(/\s+/g, '_').slice(0, 80) || 'projekt';
export const uuid = () => crypto.randomUUID();
