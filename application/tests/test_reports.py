import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from reports.models import Report
from sharepoint.graph import SharePointError
from tests.helpers import make_project, patch_json, pdf_file

pytestmark = pytest.mark.django_db

DOCX = b'PK\x03\x04 test'
SP_SETTINGS = {'sp_site_url': 'https://firma.sharepoint.com/sites/Odbiory', 'sp_library': 'Dokumenty'}


def upload(client, project, **extra):
    body = {'kind': 'pdf', 'document_date': '2026-11-17', 'file': pdf_file(), **extra}
    return client.post(f"/api/projects/{project['id']}/reports", body)


@pytest.fixture
def microsoft_api(api, monkeypatch):
    """Klient zalogowany tokenem Microsoft (potrzebny do zapisu w SharePoint)."""
    from django.test import Client

    monkeypatch.setattr('core.entra.validate_token', lambda t: {'oid': 'o', 'tid': 'tenant', 'preferred_username': 'jan.kowalski@firma.pl'})
    return Client(headers={'Authorization': 'Bearer ms-token'})


def test_create_list_download_delete(api, project):
    r = upload(api, project, defects_count=3, defect_filter='open')
    assert r.status_code == 201
    report = r.json()
    assert report['filename'] == 'Protokol_usterek_Osiedle_Zielone_17-11-2026.pdf'
    assert (report['sharepoint_status'], report['defects_count'], report['created_by']) == ('none', 3, 'Jan Kowalski')
    assert [x['id'] for x in api.get(f"/api/projects/{project['id']}/reports").json()] == [report['id']]

    download = api.get(f"/api/reports/{report['id']}/file")
    download.close()
    assert download.status_code == 200 and 'attachment' in download['Content-Disposition']
    assert api.delete(f"/api/reports/{report['id']}").status_code == 204
    assert not Report.objects.exists()


def test_word_report_is_accepted(api, project):
    docx = SimpleUploadedFile('r.docx', DOCX)
    assert upload(api, project, kind='docx', file=docx).json()['filename'].endswith('.docx')


@pytest.mark.parametrize('kind, payload', [
    ('xls', pdf_file()),
    ('pdf', SimpleUploadedFile('r.pdf', b'to nie pdf')),
    ('docx', pdf_file()),
])
def test_rejects_wrong_kind_or_content(api, project, kind, payload):
    assert upload(api, project, kind=kind, file=payload).status_code == 400


def test_rejects_too_large_report(api, project, monkeypatch):
    monkeypatch.setattr('reports.api.MAX_REPORT', 5)
    assert upload(api, project).status_code == 413


def test_viewer_cannot_manage_reports(viewer_api, api, project):
    assert upload(viewer_api, project).status_code == 403
    report = upload(api, project).json()
    assert viewer_api.post(f"/api/reports/{report['id']}/sharepoint").status_code == 403
    assert viewer_api.delete(f"/api/reports/{report['id']}").status_code == 403
    viewer_download = viewer_api.get(f"/api/reports/{report['id']}/file")
    viewer_download.close()
    assert viewer_download.status_code == 200


def test_reports_are_isolated_between_organizations(api, other_api, project):
    report = upload(api, project).json()
    assert other_api.get(f"/api/reports/{report['id']}/file").status_code == 404
    assert other_api.delete(f"/api/reports/{report['id']}").status_code == 404
    assert other_api.get(f"/api/projects/{project['id']}/reports").status_code == 404


class TestSharePoint:
    def test_requires_organization_settings(self, api, project):
        assert upload(api, project, send_to_sharepoint='true').status_code == 400

    def test_requires_microsoft_login(self, api, project):
        patch_json(api, '/api/organization/', SP_SETTINGS)
        report = upload(api, project, send_to_sharepoint='true').json()
        assert report['sharepoint_status'] == 'error' and 'Microsoft' in report['sharepoint_error']

    def test_success(self, microsoft_api, api, project, monkeypatch):
        patch_json(api, '/api/organization/', {**SP_SETTINGS, 'sp_folder': 'Usterki/{inwestycja}'})
        captured = {}

        def fake_upload(**kw):
            captured.update(kw)
            return {'web_url': 'https://firma.sharepoint.com/x.pdf', 'path': 'Usterki/Osiedle Zielone/x.pdf'}

        monkeypatch.setattr('reports.api.upload_report', fake_upload)
        report = upload(microsoft_api, project, send_to_sharepoint='true').json()
        assert report['sharepoint_status'] == 'ok' and report['sharepoint_url'].endswith('x.pdf')
        assert captured['folder'] == 'Usterki/Osiedle Zielone' and captured['data'].startswith(b'%PDF')

    def test_known_sharepoint_error_is_stored(self, microsoft_api, api, project, monkeypatch):
        patch_json(api, '/api/organization/', SP_SETTINGS)

        def refuse(**kw):
            raise SharePointError('Brak uprawnień')

        monkeypatch.setattr('reports.api.upload_report', refuse)
        report = upload(microsoft_api, project, send_to_sharepoint='true').json()
        assert (report['sharepoint_status'], report['sharepoint_error']) == ('error', 'Brak uprawnień')

    def test_unexpected_error_does_not_lose_the_report(self, microsoft_api, api, project, monkeypatch, caplog):
        patch_json(api, '/api/organization/', SP_SETTINGS)

        def crash(**kw):
            raise ConnectionError('sieć')

        monkeypatch.setattr('reports.api.upload_report', crash)
        with caplog.at_level('ERROR'):
            report = upload(microsoft_api, project, send_to_sharepoint='true').json()
        assert report['sharepoint_status'] == 'error' and 'Nieoczekiwany' in report['sharepoint_error']
        assert Report.objects.count() == 1 and 'SharePoint upload failed' in caplog.text

    def test_retry_after_failure(self, microsoft_api, api, project, monkeypatch):
        patch_json(api, '/api/organization/', SP_SETTINGS)
        report = upload(api, project).json()
        monkeypatch.setattr('reports.api.upload_report', lambda **kw: {'web_url': 'https://x', 'path': 'p'})
        retried = microsoft_api.post(f"/api/reports/{report['id']}/sharepoint").json()
        assert retried['sharepoint_status'] == 'ok' and retried['sharepoint_error'] == ''


def test_report_filename_is_sanitized(api, pro):
    project = make_project(api, name='A/B: "test"?')
    name = upload(api, project).json()['filename']
    assert '/' not in name and ':' not in name and '"' not in name
