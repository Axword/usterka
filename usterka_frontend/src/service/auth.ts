import Http from './http';
import { rest } from './rest';
import type { AuthConfig, InvitationInfo, Me } from 'src/types/api';

const anon = new Http();

export const AuthService = {
  config: async () => (await anon.http.get<AuthConfig>('auth/config')).data,
  devLogin: async (email: string, name = '') => (await anon.http.post<{ token: string }>('auth/dev-login', { email, name })).data,
  register: async (d: { email: string; password: string; name: string; company: string }) =>
    (await anon.http.post<{ token: string }>('auth/register', d)).data,
  login: async (email: string, password: string) => (await anon.http.post<{ token: string }>('auth/login', { email, password })).data,
  forgotPassword: async (email: string) => (await anon.http.post<{ ok: boolean }>('auth/password-reset', { email })).data,
  resetPassword: async (uid: string, token: string, password: string) =>
    (await anon.http.post<{ token: string }>('auth/password-reset/confirm', { uid, token, password })).data,
  verifyEmail: async (token: string) => (await anon.http.post<{ ok: boolean }>('auth/verify-email', { token })).data,
  resendVerification: () => rest.post<{ ok: boolean }>('auth/resend-verification'),
  invitation: async (token: string) => (await anon.http.get<InvitationInfo>(`auth/invitations/${token}`)).data,
  acceptInvitation: async (token: string, password: string, name: string) =>
    (await anon.http.post<{ token: string }>(`auth/invitations/${token}/accept`, { password, name })).data,
  me: () => rest.get<Me>('auth/me'),
};
