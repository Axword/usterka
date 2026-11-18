"""Klient Microsoft Graph. HTTP jest atrapowany biblioteką `responses`, MSAL fałszywym obiektem."""

import pytest
import responses
from django.test import override_settings

from sharepoint import graph
from sharepoint.graph import GRAPH, Graph, SharePointError, safe_segment, target_folder, upload_report

SITE_URL = 'https://firma.sharepoint.com/sites/Odbiory'
SITE_API = f'{GRAPH}/sites/firma.sharepoint.com:/sites/Odbiory'


class FakeMsal:
    result = {'access_token': 'graph-token'}
    seen = {}

    def __init__(self, client_id, authority, client_credential):
        FakeMsal.seen = {'client_id': client_id, 'authority': authority, 'secret': client_credential}

    def acquire_token_on_behalf_of(self, assertion, scopes):
        FakeMsal.seen.update(assertion=assertion, scopes=scopes)
        return FakeMsal.result


@pytest.fixture
def msal_app(monkeypatch):
    monkeypatch.setattr(graph.msal, 'ConfidentialClientApplication', FakeMsal)
    FakeMsal.result = {'access_token': 'graph-token'}
    return FakeMsal


class TestOboToken:
    def test_returns_access_token(self, msal_app):
        with override_settings(ENTRA_CLIENT_SECRET='sekret'):
            assert graph.obo_token('user-token', 'tenant-1') == 'graph-token'
        assert msal_app.seen['authority'].endswith('/tenant-1') and msal_app.seen['assertion'] == 'user-token'

    def test_requires_server_configuration(self):
        with override_settings(ENTRA_CLIENT_SECRET=''), pytest.raises(SharePointError, match='ENTRA_CLIENT_SECRET'):
            graph.obo_token('t', 'x')

    @pytest.mark.parametrize('code', ['invalid_grant', 'interaction_required', 'consent_required'])
    def test_missing_consent(self, msal_app, code):
        msal_app.result = {'error': code}
        with override_settings(ENTRA_CLIENT_SECRET='s'), pytest.raises(SharePointError, match='zgody'):
            graph.obo_token('t', 'x')

    def test_other_errors_show_description(self, msal_app):
        msal_app.result = {'error': 'server_error', 'error_description': 'Awaria po stronie Microsoft'}
        with override_settings(ENTRA_CLIENT_SECRET='s'), pytest.raises(SharePointError, match='Awaria po stronie'):
            graph.obo_token('t', 'x')

    def test_other_errors_without_description(self, msal_app):
        msal_app.result = {'error': 'cos'}
        with override_settings(ENTRA_CLIENT_SECRET='s'), pytest.raises(SharePointError, match='cos'):
            graph.obo_token('t', 'x')


class TestHelpers:
    def test_safe_segment_removes_forbidden_characters(self):
        assert safe_segment(' A/B:C*D?"E<F>G|H#I%J ') == 'A B C D E F G H I J'

    @pytest.mark.parametrize('template, expected', [
        ('Usterki/{inwestycja}', 'Usterki/Osiedle  A B'),
        ('{INWESTYCJA}/Raporty', 'Osiedle  A B/Raporty'),
        ('', ''),
        (None, ''),
        ('///', ''),
    ])
    def test_target_folder(self, template, expected):
        assert target_folder(template, 'Osiedle: A/B') == expected


class TestGraphClient:
    @pytest.fixture(autouse=True)
    def _http(self):
        responses.start()
        yield
        responses.stop()
        responses.reset()

    def test_site_id(self):
        responses.get(SITE_API, json={'id': 'site-1'})
        assert Graph('t').site_id(SITE_URL + '/') == 'site-1'
        assert responses.calls[0].request.headers['Authorization'] == 'Bearer t'

    @pytest.mark.parametrize('status, message', [
        (401, 'uprawnień'), (403, 'uprawnień'), (404, 'Nie znaleziono witryny'), (500, 'błąd 500'),
    ])
    def test_http_errors(self, status, message):
        responses.get(SITE_API, status=status, body='x' * 400)
        with pytest.raises(SharePointError, match=message):
            Graph('t').site_id(SITE_URL)

    def test_empty_response_body(self):
        responses.get(SITE_API, status=200, body='')
        with pytest.raises(KeyError):
            Graph('t').site_id(SITE_URL)  # puste 200 -> {} -> brak klucza „id”

    @pytest.mark.parametrize('library', ['Dokumenty', 'dokumenty', ' /Dokumenty/ ', 'Documents'])
    def test_drive_found_by_name_or_url(self, library):
        responses.get(f'{GRAPH}/sites/s1/drives', json={'value': [
            {'id': 'd-other', 'name': 'Inna', 'webUrl': 'https://x/sites/a/Inna'},
            {'id': 'd1', 'name': 'Dokumenty', 'webUrl': 'https://firma.sharepoint.com/sites/Odbiory/Documents'},
        ]})
        assert Graph('t').drive_id('s1', library) == 'd1'

    def test_drive_not_found_lists_available(self):
        responses.get(f'{GRAPH}/sites/s1/drives', json={'value': [{'id': 'd1', 'name': 'Inna'}]})
        with pytest.raises(SharePointError, match='Dostępne: Inna'):
            Graph('t').drive_id('s1', 'Brak')

    def test_no_drives_at_all(self):
        responses.get(f'{GRAPH}/sites/s1/drives', json={})
        with pytest.raises(SharePointError, match='Dostępne: $'):
            Graph('t').drive_id('s1', 'Brak')

    def test_small_file_uses_simple_upload(self):
        url = f'{GRAPH}/drives/d1/root:/Usterki/Raport%20x.pdf:/content'
        responses.put(url, json={'webUrl': 'https://x/raport.pdf'})
        result = Graph('t').upload('d1', 'Usterki/Raport x.pdf', b'%PDF')
        assert result['webUrl'].endswith('raport.pdf')
        assert 'conflictBehavior=rename' in responses.calls[0].request.url

    def test_large_file_uses_upload_session_in_chunks(self, monkeypatch):
        monkeypatch.setattr(graph, 'SIMPLE_UPLOAD_LIMIT', 10)
        monkeypatch.setattr(graph, 'CHUNK', 8)
        responses.post(f'{GRAPH}/drives/d1/root:/raport.pdf:/createUploadSession', json={'uploadUrl': 'https://upload.test/s'})
        responses.put('https://upload.test/s', status=202, json={})
        responses.put('https://upload.test/s', status=201, json={'webUrl': 'https://x/gotowe'})
        result = Graph('t').upload('d1', 'raport.pdf', b'0123456789ABCDEF12')  # 18 B = 3 części (8+8+2)
        puts = [c.request for c in responses.calls if c.request.method == 'PUT']
        assert len(puts) == 3 and puts[0].headers['Content-Range'] == 'bytes 0-7/18' and puts[2].headers['Content-Range'] == 'bytes 16-17/18'
        assert 'Authorization' not in puts[0].headers  # uploadUrl jest już podpisany
        assert result == {'webUrl': 'https://x/gotowe'}

    def test_chunk_with_empty_body_is_handled(self, monkeypatch):
        monkeypatch.setattr(graph, 'SIMPLE_UPLOAD_LIMIT', 1)
        responses.post(f'{GRAPH}/drives/d1/root:/r.pdf:/createUploadSession', json={'uploadUrl': 'https://upload.test/s'})
        responses.put('https://upload.test/s', status=200, body='')
        assert Graph('t').upload('d1', 'r.pdf', b'abc') == {}

    def test_failed_chunk_aborts(self, monkeypatch):
        monkeypatch.setattr(graph, 'SIMPLE_UPLOAD_LIMIT', 1)
        responses.post(f'{GRAPH}/drives/d1/root:/r.pdf:/createUploadSession', json={'uploadUrl': 'https://upload.test/s'})
        responses.put('https://upload.test/s', status=500)
        with pytest.raises(SharePointError, match='Przerwany upload'):
            Graph('t').upload('d1', 'r.pdf', b'abc')


@pytest.fixture
def http():
    responses.start()
    yield
    responses.stop()
    responses.reset()


def test_upload_report_end_to_end(msal_app, http):
    responses.get(SITE_API, json={'id': 'site-1'})
    responses.get(f'{GRAPH}/sites/site-1/drives', json={'value': [{'id': 'd1', 'name': 'Dokumenty'}]})
    responses.put(f'{GRAPH}/drives/d1/root:/Usterki/Osiedle/Protokol.pdf:/content', json={'webUrl': 'https://x/p.pdf'})
    with override_settings(ENTRA_CLIENT_SECRET='s'):
        result = upload_report(user_assertion='u', tenant_id='t', site_url=SITE_URL, library='Dokumenty',
                               folder='Usterki/Osiedle', filename='Protokol.pdf', data=b'%PDF')
    assert result == {'web_url': 'https://x/p.pdf', 'path': 'Usterki/Osiedle/Protokol.pdf'}


def test_upload_report_without_folder_and_web_url(msal_app, http):
    responses.get(SITE_API, json={'id': 'site-1'})
    responses.get(f'{GRAPH}/sites/site-1/drives', json={'value': [{'id': 'd1', 'name': 'Dokumenty'}]})
    responses.put(f'{GRAPH}/drives/d1/root:/Protokol.pdf:/content', json={})
    with override_settings(ENTRA_CLIENT_SECRET='s'):
        result = upload_report(user_assertion='u', tenant_id='t', site_url=SITE_URL, library='Dokumenty',
                               folder='', filename='Protokol.pdf', data=b'%PDF')
    assert result == {'web_url': '', 'path': 'Protokol.pdf'}
