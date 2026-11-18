import Http from './http';
import { rest } from './rest';
import type { AuthConfig, Me } from 'src/types/api';

const anon = new Http();

export const AuthService = {
  config: async () => (await anon.http.get<AuthConfig>('auth/config')).data,
  devLogin: async (email: string, name = '') => (await anon.http.post<{ token: string }>('auth/dev-login', { email, name })).data,
  register: async (d: { email: string; password: string; name: string; company: string }) =>
    (await anon.http.post<{ token: string }>('auth/register', d)).data,
  login: async (email: string, password: string) => (await anon.http.post<{ token: string }>('auth/login', { email, password })).data,
  me: () => rest.get<Me>('auth/me'),
};
