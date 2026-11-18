"""Zapis plików do SharePoint w imieniu zalogowanej osoby (OAuth2 On-Behalf-Of + Microsoft Graph).

Dzięki OBO plik trafia do SharePoint z uprawnieniami tej konkretnej osoby: jeśli nie ma dostępu
do witryny/biblioteki, zapis się nie uda (zamiast zapisu „z konta aplikacji” z pełnym dostępem).
"""

import re
from urllib.parse import quote, urlparse

import msal
import requests
from django.conf import settings

GRAPH = 'https://graph.microsoft.com/v1.0'
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024
CHUNK = 320 * 1024 * 16  # 5 MiB, wielokrotność 320 KiB (wymóg Graph)
TIMEOUT = 60


class SharePointError(Exception):
    pass


def obo_token(user_assertion: str, tenant_id: str) -> str:
    if not (settings.ENTRA_CLIENT_ID and settings.ENTRA_CLIENT_SECRET):
        raise SharePointError('Serwer nie ma skonfigurowanego dostępu do Microsoft (ENTRA_CLIENT_SECRET).')
    app = msal.ConfidentialClientApplication(
        settings.ENTRA_CLIENT_ID,
        authority=f'https://login.microsoftonline.com/{tenant_id}',
        client_credential=settings.ENTRA_CLIENT_SECRET,
    )
    result = app.acquire_token_on_behalf_of(user_assertion, scopes=settings.GRAPH_SCOPES)
    if 'access_token' not in result:
        code = result.get('error', '')
        if code in ('invalid_grant', 'interaction_required', 'consent_required'):
            raise SharePointError(
                'Brak zgody na dostęp do SharePoint. Administrator musi zatwierdzić uprawnienia aplikacji.'
            )
        raise SharePointError(f"Nie udało się uzyskać dostępu do SharePoint: {result.get('error_description', code)}")
    return result['access_token']


def safe_segment(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|#%]+', ' ', str(s)).strip()


def target_folder(template: str, project_name: str) -> str:
    name = safe_segment(project_name)
    folder = (template or '').replace('{inwestycja}', name).replace('{INWESTYCJA}', name)
    return '/'.join(safe_segment(p) for p in folder.split('/') if safe_segment(p))


class Graph:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers['Authorization'] = f'Bearer {token}'

    def _check(self, r: requests.Response):
        if r.status_code in (401, 403):
            raise SharePointError('Nie masz uprawnień do zapisu w tej witrynie lub bibliotece SharePoint.')
        if r.status_code == 404:
            raise SharePointError('Nie znaleziono witryny lub biblioteki SharePoint. Sprawdź ustawienia organizacji.')
        if not r.ok:
            raise SharePointError(f'SharePoint zwrócił błąd {r.status_code}: {r.text[:300]}')
        return r.json() if r.content else {}

    def site_id(self, site_url: str) -> str:
        u = urlparse(site_url)
        return self._check(self.s.get(f'{GRAPH}/sites/{u.hostname}:{u.path.rstrip("/")}', timeout=TIMEOUT))['id']

    def drive_id(self, site_id: str, library: str) -> str:
        drives = self._check(self.s.get(f'{GRAPH}/sites/{site_id}/drives', timeout=TIMEOUT)).get('value', [])
        lib = library.strip().strip('/').lower()
        for d in drives:
            url_tail = (d.get('webUrl') or '').rstrip('/').rsplit('/', 1)[-1]
            if d.get('name', '').lower() == lib or requests.utils.unquote(url_tail).lower() == lib:
                return d['id']
        names = ', '.join(d.get('name', '') for d in drives)
        raise SharePointError(f'Nie znaleziono biblioteki „{library}”. Dostępne: {names}')

    def upload(self, drive_id: str, path: str, data: bytes) -> dict:
        p = quote(path)
        if len(data) <= SIMPLE_UPLOAD_LIMIT:
            r = self.s.put(f'{GRAPH}/drives/{drive_id}/root:/{p}:/content?@microsoft.graph.conflictBehavior=rename',
                           data=data, timeout=TIMEOUT)
            return self._check(r)
        sess = self._check(self.s.post(
            f'{GRAPH}/drives/{drive_id}/root:/{p}:/createUploadSession',
            json={'item': {'@microsoft.graph.conflictBehavior': 'rename'}}, timeout=TIMEOUT,
        ))
        url, total, result = sess['uploadUrl'], len(data), {}
        for start in range(0, total, CHUNK):
            chunk = data[start:start + CHUNK]
            end = start + len(chunk) - 1
            # uploadUrl jest już podpisany - bez nagłówka Authorization
            r = requests.put(url, data=chunk, timeout=TIMEOUT * 2, headers={
                'Content-Length': str(len(chunk)), 'Content-Range': f'bytes {start}-{end}/{total}'})
            if r.status_code not in (200, 201, 202):
                raise SharePointError(f'Przerwany upload do SharePoint ({r.status_code}).')
            result = r.json() if r.content else {}
        return result


def upload_report(*, user_assertion: str, tenant_id: str, site_url: str, library: str, folder: str,
                  filename: str, data: bytes) -> dict:
    g = Graph(obo_token(user_assertion, tenant_id))
    site = g.site_id(site_url)
    drive = g.drive_id(site, library)
    path = '/'.join(x for x in [folder, safe_segment(filename)] if x)
    item = g.upload(drive, path, data)
    return {'web_url': item.get('webUrl', ''), 'path': path}
