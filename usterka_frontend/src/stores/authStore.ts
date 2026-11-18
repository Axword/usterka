import { create } from 'zustand';
import { AuthService } from 'src/service/auth';
import { initMsal, loginMicrosoft, logoutMicrosoft, msalAccount } from 'src/service/msal';
import State from 'src/service/state';
import type { AuthConfig, Me } from 'src/types/api';

type Status = 'loading' | 'anonymous' | 'ready' | 'error';

interface AuthState {
  status: Status;
  error: string | null;
  config: AuthConfig | null;
  me: Me | null;
  init: () => Promise<void>;
  devLogin: (email: string, name?: string) => Promise<void>;
  passwordLogin: (email: string, password: string) => Promise<void>;
  register: (d: { email: string; password: string; name: string; company: string }) => Promise<void>;
  microsoftLogin: () => Promise<void>;
  logout: () => Promise<void>;
  canWrite: () => boolean;
}

export const useAuth = create<AuthState>((set, get) => ({
  status: 'loading',
  error: null,
  config: null,
  me: null,

  async init() {
    try {
      const config = await AuthService.config();
      set({ config });
      await initMsal(config);
      if (config.microsoft && msalAccount() && State.getMode() !== 'dev') State.setMicrosoft();
      if (!State.isAuthenticated()) return set({ status: 'anonymous' });
      const me = await AuthService.me();
      set({ me, status: 'ready' });
    } catch (e) {
      if (!State.isAuthenticated()) return set({ status: 'anonymous' });
      State.clearAuth();
      set({ status: 'anonymous', error: e instanceof Error ? e.message : String(e) });
    }
  },

  async devLogin(email, name) {
    const { token } = await AuthService.devLogin(email, name);
    State.setDevToken(token);
    const me = await AuthService.me();
    set({ me, status: 'ready' });
  },

  // Token własny (hasło) jest przechowywany jak token dev - tryb „own token” w State.
  async passwordLogin(email, password) {
    const { token } = await AuthService.login(email, password);
    State.setDevToken(token);
    set({ me: await AuthService.me(), status: 'ready' });
  },

  async register(d) {
    const { token } = await AuthService.register(d);
    State.setDevToken(token);
    set({ me: await AuthService.me(), status: 'ready' });
  },

  async microsoftLogin() {
    State.setMicrosoft();
    await loginMicrosoft(); // przekierowanie - po powrocie init() dokończy logowanie
  },

  async logout() {
    const wasMs = State.getMode() === 'microsoft';
    State.clearAuth();
    set({ me: null, status: 'anonymous' });
    if (wasMs) await logoutMicrosoft();
  },

  canWrite: () => {
    const r = get().me?.role;
    return r === 'admin' || r === 'inspector';
  },
}));
