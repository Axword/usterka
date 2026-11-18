/** Trwały stan logowania w localStorage (wzorem lol_spy/service/state.js). */
export type AuthMode = 'dev' | 'microsoft';

const K = { mode: 'usterka.authMode', token: 'usterka.devToken' };

export default class State {
  static setDevToken(token: string) {
    localStorage.setItem(K.mode, 'dev');
    localStorage.setItem(K.token, token);
  }

  static setMicrosoft() {
    localStorage.setItem(K.mode, 'microsoft');
    localStorage.removeItem(K.token);
  }

  static getMode(): AuthMode | null {
    return localStorage.getItem(K.mode) as AuthMode | null;
  }

  static getDevToken(): string | null {
    return localStorage.getItem(K.token);
  }

  static clearAuth() {
    localStorage.removeItem(K.mode);
    localStorage.removeItem(K.token);
  }

  static isAuthenticated(): boolean {
    return !!this.getMode();
  }
}
