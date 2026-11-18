import axios, { type AxiosInstance } from 'axios';

export const apiBaseUrl = (): string => import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/';

/** Klient bez logowania (wzorem lol_spy/service/http.js). */
export default class Http {
  http: AxiosInstance;

  constructor() {
    this.http = axios.create({ baseURL: apiBaseUrl(), headers: { 'Content-Type': 'application/json' } });
  }
}

export function errorMessage(e: unknown, fallback = 'Wystąpił błąd.'): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { detail?: unknown } | undefined;
    if (typeof d?.detail === 'string') return d.detail;
    if (Array.isArray(d?.detail)) return 'Niepoprawne dane formularza.';
    if (!e.response) return 'Brak połączenia z serwerem.';
  }
  return e instanceof Error ? e.message : fallback;
}
