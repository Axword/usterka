import { create } from 'zustand';

export interface DialogOptions {
  title: string;
  text?: string;
  input?: string;
  okLabel?: string;
  cancelLabel?: string | null;
  danger?: boolean;
}

interface DialogState extends DialogOptions {
  resolve: (v: string | boolean | null) => void;
}

interface UiState {
  toasts: { id: number; text: string }[];
  busy: string | null;
  dialog: DialogState | null;
  lightbox: string | null;
  setBusy: (t: string | null) => void;
  setLightbox: (src: string | null) => void;
}

export const useUi = create<UiState>((set) => ({
  toasts: [],
  busy: null,
  dialog: null,
  lightbox: null,
  setBusy: (busy) => set({ busy }),
  setLightbox: (lightbox) => set({ lightbox }),
}));

let seq = 0;
export function toast(text: string, ms = 3200) {
  const id = ++seq;
  useUi.setState((s) => ({ toasts: [...s.toasts, { id, text }] }));
  setTimeout(() => useUi.setState((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), ms);
}

export const busy = (t: string | null) => useUi.getState().setBusy(t);

/** Okno potwierdzenia / pola tekstowego. Zwraca: true/false (bez input) albo tekst/null (z input). */
export function dialog(o: DialogOptions & { input: string }): Promise<string | null>;
export function dialog(o: DialogOptions): Promise<boolean>;
export function dialog(o: DialogOptions): Promise<string | boolean | null> {
  return new Promise((resolve) => {
    useUi.setState({
      dialog: {
        okLabel: 'OK',
        cancelLabel: 'Anuluj',
        ...o,
        resolve: (v) => {
          useUi.setState({ dialog: null });
          resolve(v);
        },
      },
    });
  });
}

export async function withBusy<T>(text: string, fn: () => Promise<T>): Promise<T> {
  busy(text);
  try {
    return await fn();
  } finally {
    busy(null);
  }
}
