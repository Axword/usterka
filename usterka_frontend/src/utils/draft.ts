import type { DueMode } from 'src/types/api';

/** Szkic formularza usterki (autosave). Zdjęcia nie są w szkicu - tylko pola tekstowe i położenie. */
export interface DefectDraft {
  projectId: string;
  planId: string;
  defectId: string | null;
  no: number | null;
  type: string;
  typeOther: string;
  desc: string;
  dueMode: DueMode | '';
  dueDate: string;
  zoom: number;
  x: number;
  y: number;
  fixedDate: string;
  savedAt: number;
}

const KEY = 'usterka.defectDraft';

export const saveDraft = (d: DefectDraft) => {
  try {
    localStorage.setItem(KEY, JSON.stringify(d));
  } catch {
    /* brak miejsca - pomijamy */
  }
};

export const loadDraft = (): DefectDraft | null => {
  try {
    return JSON.parse(localStorage.getItem(KEY) || 'null');
  } catch {
    return null;
  }
};

export const clearDraft = () => localStorage.removeItem(KEY);
