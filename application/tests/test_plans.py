import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from tests.helpers import image_file, jpeg, make_plan, make_project, patch_json, post_json

pytestmark = pytest.mark.django_db


def test_create_list_and_download_plan(api, project):
    plan = make_plan(api, project['id'])
    assert (plan['width'], plan['height']) == (400, 300)
    assert [p['id'] for p in api.get(f"/api/projects/{project['id']}/plans").json()] == [plan['id']]
    r = api.get(f"/api/plans/{plan['id']}/image")
    assert r.status_code == 200 and r['Content-Type'] == 'image/jpeg' and r['Cache-Control'].startswith('private')


def test_plan_requires_complete_project(api, pro):
    incomplete = post_json(api, '/api/projects/', {'name': 'X'}).json()
    r = api.post(f"/api/projects/{incomplete['id']}/plans", {'name': 'P', 'image': jpeg()})
    assert r.status_code == 400


def test_blank_name_falls_back_to_default(api, project):
    r = api.post(f"/api/projects/{project['id']}/plans", {'name': '   ', 'image': jpeg()})
    assert r.json()['name'] == 'Plan'


@pytest.mark.parametrize('payload, status', [
    (SimpleUploadedFile('x.jpg', b'not an image', content_type='image/jpeg'), 400),
    (image_file('GIF'), 400),  # poprawny obraz, ale niedozwolony format
])
def test_rejects_invalid_images(api, project, payload, status):
    r = api.post(f"/api/projects/{project['id']}/plans", {'name': 'P', 'image': payload})
    assert r.status_code == status


def test_rejects_too_large_file(api, project, monkeypatch):
    monkeypatch.setattr('core.files.Image.MAX_IMAGE_PIXELS', 10)  # każdy większy obraz to „bomba dekompresji”
    r = api.post(f"/api/projects/{project['id']}/plans", {'name': 'P', 'image': jpeg()})
    assert r.status_code == 400


def test_upload_size_limit(api, project):
    big = SimpleUploadedFile('x.jpg', b'0' * (41 * 1024 * 1024), content_type='image/jpeg')
    r = api.post(f"/api/projects/{project['id']}/plans", {'name': 'P', 'image': big})
    assert r.status_code == 413


def test_rename_plan(api, plan):
    r = patch_json(api, f"/api/plans/{plan['id']}", {'name': '  Piętro 1  '})
    assert r.json()['name'] == 'Piętro 1'


def test_rename_to_blank_is_rejected(api, plan):
    assert patch_json(api, f"/api/plans/{plan['id']}", {'name': ' '}).status_code == 400


def test_delete_plan_removes_file_and_defects(api, project, plan, settings):
    from tests.helpers import make_defect

    d = make_defect(api, project['id'], plan['id']).json()
    assert api.delete(f"/api/plans/{plan['id']}").status_code == 204
    assert api.get(f"/api/defects/{d['id']}").status_code == 404
    assert not any(settings.MEDIA_ROOT.rglob('*.jpg'))


def test_viewer_cannot_modify_plans(viewer_api, api, project, plan):
    assert viewer_api.post(f"/api/projects/{project['id']}/plans", {'name': 'P', 'image': jpeg()}).status_code == 403
    assert patch_json(viewer_api, f"/api/plans/{plan['id']}", {'name': 'X'}).status_code == 403
    assert viewer_api.delete(f"/api/plans/{plan['id']}").status_code == 403
    assert viewer_api.get(f"/api/plans/{plan['id']}/image").status_code == 200


def test_plan_from_another_org_is_hidden(other_api, plan):
    assert other_api.get(f"/api/plans/{plan['id']}/image").status_code == 404
    assert other_api.delete(f"/api/plans/{plan['id']}").status_code == 404


def test_str_representation(project, plan):
    from plans.models import Plan
    from projects.models import Project

    assert str(Plan.objects.get(pk=plan['id'])) == plan['name']
    assert str(Project.objects.get(pk=project['id'])) == project['name']


def test_make_project_helper_with_overrides(api, pro):
    assert make_project(api, name='Inna')['name'] == 'Inna'
