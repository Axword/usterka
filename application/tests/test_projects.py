import pytest

from projects.models import Project
from tests.helpers import PROJECT, image_file, make_plan, make_project, patch_json, post_json

pytestmark = pytest.mark.django_db


def test_create_and_read_project(api, pro):
    p = make_project(api)
    assert p['is_complete'] and p['plans_count'] == 0 and not p['has_logo']
    assert api.get(f"/api/projects/{p['id']}").json()['name'] == PROJECT['name']
    assert [x['id'] for x in api.get('/api/projects/').json()] == [p['id']]


def test_project_name_is_required(api):
    assert post_json(api, '/api/projects/', {'name': '   '}).status_code == 422


def test_incomplete_project_is_flagged(api):
    r = post_json(api, '/api/projects/', {'name': 'X'})
    assert r.status_code == 201 and r.json()['is_complete'] is False


def test_start_plan_allows_only_one_project(api):
    make_project(api)
    r = post_json(api, '/api/projects/', {'name': 'Druga'})
    assert r.status_code == 402 and 'Start' in r.json()['detail']


def test_viewer_cannot_create_or_edit(viewer_api, api, pro):
    assert post_json(viewer_api, '/api/projects/', {'name': 'X'}).status_code == 403
    p = make_project(api)
    assert patch_json(viewer_api, f"/api/projects/{p['id']}", {'name': 'Zmiana'}).status_code == 403
    assert viewer_api.get(f"/api/projects/{p['id']}").status_code == 200  # podgląd wolno


def test_update_project(api, project):
    r = patch_json(api, f"/api/projects/{project['id']}", {'name': '  Nowa nazwa  ', 'author': 'Ola'})
    assert r.status_code == 200
    assert (r.json()['name'], r.json()['author']) == ('Nowa nazwa', 'Ola')


def test_update_with_blank_name_is_rejected_by_model_validation(api, project):
    r = patch_json(api, f"/api/projects/{project['id']}", {'name': ''})
    assert r.status_code == 400  # ValidationError -> handler w core.errors


def test_malformed_id_gives_400_not_500(api):
    assert api.get('/api/projects/to-nie-uuid').status_code == 400


def test_other_organization_cannot_see_project(api, other_api, project):
    assert other_api.get(f"/api/projects/{project['id']}").status_code == 404
    assert other_api.get('/api/projects/').json() == []


def test_delete_project_removes_it_and_its_files(api, project, plan, settings):
    assert any(settings.MEDIA_ROOT.rglob('*.jpg'))
    assert api.delete(f"/api/projects/{project['id']}").status_code == 204
    assert not Project.objects.exists()
    assert not any(settings.MEDIA_ROOT.rglob('*.jpg'))  # sygnał usunął plik planu


def test_counts_in_project_list(api, project, plan):
    from tests.helpers import add_photo, make_defect

    d1 = make_defect(api, project['id'], plan['id']).json()
    make_defect(api, project['id'], plan['id'])
    add_photo(api, d1['id'], 'after')
    row = api.get('/api/projects/').json()[0]
    assert (row['plans_count'], row['open_count'], row['fixed_count']) == (1, 1, 1)


def test_save_report_settings(api, project):
    body = {'date': '2026-11-18', 'filter': 'open', 'plans': False, 'logo': True, 'sharepoint': False}
    r = api.put(f"/api/projects/{project['id']}/report-settings", data=body, content_type='application/json')
    assert r.status_code == 200
    assert r.json()['report_settings']['filter'] == 'open'


class TestLogo:
    def url(self, project):
        return f"/api/projects/{project['id']}/logo"

    def test_upload_replace_download_and_delete(self, api, project, settings):
        r = api.post(self.url(project), {'file': image_file('PNG')})
        assert r.status_code == 200 and r.json()['has_logo'] is True
        first = next(settings.MEDIA_ROOT.rglob('*.png'))
        download = api.get(self.url(project))
        download.close()  # strumień trzyma uchwyt pliku (Windows nie pozwoli go potem usunąć)
        assert download.status_code == 200

        api.post(self.url(project), {'file': image_file('PNG')})  # zamiana usuwa stary plik
        assert not first.exists() and len(list(settings.MEDIA_ROOT.rglob('*.png'))) == 1

        r = api.delete(self.url(project))
        assert r.json()['has_logo'] is False and not any(settings.MEDIA_ROOT.rglob('*.png'))

    def test_delete_without_logo_is_harmless(self, api, project):
        assert api.delete(self.url(project)).json()['has_logo'] is False

    def test_download_without_logo_is_404(self, api, project):
        assert api.get(self.url(project)).status_code == 404

    def test_rejects_non_image(self, api, project):
        from django.core.files.uploadedfile import SimpleUploadedFile

        bad = SimpleUploadedFile('x.png', b'to nie obraz', content_type='image/png')
        assert api.post(self.url(project), {'file': bad}).status_code == 400


def test_plan_image_is_isolated_between_orgs(api, other_api, project):
    plan = make_plan(api, project['id'])
    assert other_api.get(f"/api/plans/{plan['id']}/image").status_code == 404
