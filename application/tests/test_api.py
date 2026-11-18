import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

PROJECT = {
    'name': 'Osiedle Zielone', 'address': 'ul. Polna 1, Warszawa', 'investor': 'Inwestor SA',
    'contractor': 'Budex', 'inspection_date': '2026-11-17', 'author': 'Jan Kowalski',
}


def jpeg(w=400, h=300):
    b = io.BytesIO()
    Image.new('RGB', (w, h), 'white').save(b, 'JPEG')
    return SimpleUploadedFile('plan.jpg', b.getvalue(), content_type='image/jpeg')


def make_project(api):
    r = api.post('/api/projects/', PROJECT, content_type='application/json')
    assert r.status_code == 201, r.content
    return r.json()


def make_plan(api, pid):
    r = api.post(f'/api/projects/{pid}/plans', {'name': 'Parter', 'image': jpeg()})
    assert r.status_code == 201, r.content
    return r.json()


def make_defect(api, pid, plan_id, **kw):
    body = {'plan_id': plan_id, 'x': .5, 'y': .5, 'type': 'Budowlana', 'description': 'Rysa na ścianie',
            'due_mode': 'umowa', **kw}
    return api.post(f'/api/projects/{pid}/defects', body, content_type='application/json')


@pytest.mark.django_db
def test_requires_auth(client):
    assert client.get('/api/projects/').status_code == 401
    assert client.get('/api/auth/config').status_code == 200


@pytest.mark.django_db
def test_me_and_org(api):
    me = api.get('/api/auth/me').json()
    assert me['role'] == 'admin' and me['organization_name'] == 'firma.pl'


@pytest.mark.django_db
def test_full_flow(api):
    p = make_project(api)
    assert p['is_complete']
    plan = make_plan(api, p['id'])
    assert (plan['width'], plan['height']) == (400, 300)
    assert api.get(f"/api/plans/{plan['id']}/image").status_code == 200

    d1 = make_defect(api, p['id'], plan['id']).json()
    d2 = make_defect(api, p['id'], plan['id']).json()
    assert (d1['no'], d2['no']) == (1, 2)
    assert d1['status'] == 'open'

    r = api.post(f"/api/defects/{d1['id']}/photos", {'kind': 'after', 'file': jpeg(100, 100)})
    assert r.status_code == 201
    d = r.json()
    assert d['status'] == 'fixed' and d['fixed_date']

    r = api.delete(f"/api/photos/{d['photos'][0]['id']}")
    assert r.json()['status'] == 'open'

    proj = api.get(f"/api/projects/{p['id']}").json()
    assert (proj['open_count'], proj['plans_count']) == (2, 1)

    r = api.patch(f"/api/defects/{d2['id']}", {'description': 'Nowy opis'}, content_type='application/json')
    assert r.json()['description'] == 'Nowy opis'
    events = api.get(f"/api/defects/{d2['id']}/events").json()
    assert events[0]['action'] == 'updated'

    assert api.delete(f"/api/projects/{p['id']}").status_code == 204


@pytest.mark.django_db
def test_validation(api, user):
    from billing.services import activate_demo
    from organizations.models import Membership

    activate_demo(Membership.objects.get(user=user).organization, 'pro')  # limit planu Start to 1 inwestycja
    p = make_project(api)
    plan = make_plan(api, p['id'])
    assert make_defect(api, p['id'], plan['id'], type='Nieznany').status_code == 400
    assert make_defect(api, p['id'], plan['id'], due_mode='data').status_code == 400
    incomplete = api.post('/api/projects/', {'name': 'X'}, content_type='application/json').json()
    assert api.post(f"/api/projects/{incomplete['id']}/plans", {'name': 'P', 'image': jpeg()}).status_code == 400
    bad = SimpleUploadedFile('x.jpg', b'not an image', content_type='image/jpeg')
    assert api.post(f"/api/projects/{p['id']}/plans", {'name': 'P', 'image': bad}).status_code == 400


@pytest.mark.django_db
def test_isolation_between_orgs(api, other_api):
    p = make_project(api)
    assert other_api.get(f"/api/projects/{p['id']}").status_code == 404
    assert other_api.get('/api/projects/').json() == []


@pytest.mark.django_db
def test_report_upload_without_microsoft(api):
    p = make_project(api)
    pdf = SimpleUploadedFile('r.pdf', b'%PDF-1.4 test', content_type='application/pdf')
    r = api.post(f"/api/projects/{p['id']}/reports", {'kind': 'pdf', 'document_date': '2026-11-17', 'file': pdf})
    assert r.status_code == 201
    rep = r.json()
    assert rep['sharepoint_status'] == 'none'
    assert api.get(f"/api/reports/{rep['id']}/file").status_code == 200
    api.patch('/api/organization/', {'sp_site_url': 'https://firma.sharepoint.com/sites/Odbiory', 'sp_library': 'Dokumenty'},
              content_type='application/json')
    rep = api.post(f"/api/reports/{rep['id']}/sharepoint").json()
    assert rep['sharepoint_status'] == 'error' and 'Microsoft' in rep['sharepoint_error']


def test_target_folder():
    from sharepoint.graph import target_folder
    assert target_folder('Usterki/{inwestycja}', 'Osiedle: A/B') == 'Usterki/Osiedle  A B'
