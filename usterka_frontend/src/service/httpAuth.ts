import Http, { errorMessage } from './http';
import State from './state';
import { msalApiToken } from './msal';
import { toast } from 'src/stores/uiStore';

let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => {
  onUnauthorized = fn;
};

export async function bearerToken(): Promise<string | null> {
  const mode = State.getMode();
  if (mode === 'dev') return State.getDevToken();
  if (mode === 'microsoft') return msalApiToken();
  return null;
}

/** Klient z tokenem: dev-token albo token Microsoft pobierany na bieżąco (odświeżanie robi MSAL). */
export default class AuthHttp extends Http {
  constructor() {
    super();
    this.http.interceptors.request.use(async (config) => {
      const token = await bearerToken();
      if (token) config.headers.Authorization = `Bearer ${token}`;
      return config;
    });
    this.http.interceptors.response.use(
      (r) => r,
      (error) => {
        if (error?.code === 'ERR_CANCELED') return Promise.reject(error);
        const status = error?.response?.status;
        if (status === 401) {
          State.clearAuth();
          toast('Sesja wygasła. Zaloguj się ponownie.');
          onUnauthorized();
        } else if (status === 403) {
          toast(errorMessage(error, 'Brak uprawnień.'));
        } else if (!error?.response) {
          toast('Brak połączenia z serwerem.');
        }
        return Promise.reject(error);
      },
    );
  }
}
