import {
  InteractionRequiredAuthError,
  PublicClientApplication,
  type AccountInfo,
} from '@azure/msal-browser';
import type { AuthConfig } from 'src/types/api';

/** Logowanie kontem Microsoft (Entra ID). Każda osoba loguje się swoim kontem służbowym. */
let pca: PublicClientApplication | null = null;
let scope = '';

export async function initMsal(cfg: AuthConfig): Promise<void> {
  if (!cfg.microsoft || pca) return;
  scope = cfg.api_scope;
  pca = new PublicClientApplication({
    auth: {
      clientId: cfg.client_id,
      authority: `https://login.microsoftonline.com/${cfg.tenant}`,
      redirectUri: window.location.origin,
      postLogoutRedirectUri: window.location.origin,
    },
    cache: { cacheLocation: 'localStorage' },
  });
  await pca.initialize();
  const res = await pca.handleRedirectPromise();
  if (res?.account) pca.setActiveAccount(res.account);
  if (!pca.getActiveAccount()) {
    const [first] = pca.getAllAccounts();
    if (first) pca.setActiveAccount(first);
  }
}

export function msalAccount(): AccountInfo | null {
  return pca?.getActiveAccount() ?? null;
}

export async function loginMicrosoft(): Promise<void> {
  if (!pca) throw new Error('Logowanie Microsoft nie jest skonfigurowane.');
  await pca.loginRedirect({ scopes: [scope], prompt: 'select_account' });
}

/** Access token dla naszego API. Backend wymienia go (On-Behalf-Of) na token do SharePoint. */
export async function msalApiToken(): Promise<string> {
  const account = msalAccount();
  if (!pca || !account) throw new Error('Brak sesji Microsoft.');
  try {
    const r = await pca.acquireTokenSilent({ scopes: [scope], account });
    return r.accessToken;
  } catch (e) {
    if (e instanceof InteractionRequiredAuthError) {
      await pca.acquireTokenRedirect({ scopes: [scope], account });
    }
    throw e;
  }
}

export async function logoutMicrosoft(): Promise<void> {
  const account = msalAccount();
  if (pca && account) await pca.logoutRedirect({ account });
}
