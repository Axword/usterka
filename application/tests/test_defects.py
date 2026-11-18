import datetime as dt
import uuid

import pytest
from django.utils import timezone

from defects.models import Defect, DefectEvent, Photo
from tests.helpers import add_photo, defect_body, jpeg, make_defect, make_plan, make_project, patch_json, post_json

pytestmark = pytest.mark.django_db


@pytest.fixture
def defect(api, project, plan):
    return make_defect(api, project['id'], plan['id']).json()


class TestCreate:
    def test_numbers_are_sequential_per_project(self, api, project, plan):
        numbers = [make_defect(api, project['id'], plan['id']).json()['no'] for _ in range(3)]
        assert numbers == [1, 2, 3]

    def test_numbering_is_independent_between_projects(self, api, project, plan):
        make_defect(api, project['id'], plan['id'])
        second = make_project(api, name='Druga inwestycja')
        plan2 = make_plan(api, second['id'])
        assert make_defect(api, second['id'], plan2['id']).json()['no'] == 1

    def test_client_supplied_id_is_used_once(self, api, project, plan):
        cid = str(uuid.uuid4())
        first = make_defect(api, project['id'], plan['id'], id=cid)
        again = make_defect(api, project['id'], plan['id'], id=cid)  # kolizja: serwer nadaje własny id
        assert first.json()['id'] == cid and again.json()['id'] != cid

    def test_creation_is_logged(self, api, defect):
        events = api.get(f"/api/defects/{defect['id']}/events").json()
        assert [e['action'] for e in events] == ['created'] and events[0]['user'] == 'Jan Kowalski'

    @pytest.mark.parametrize('override', [
        {'type': 'Nieznany'}, {'description': '   '}, {'due_mode': 'data'}, {'due_mode': 'kiedys'}, {'x': 1.5}, {'y': -0.1},
    ])
    def test_validation_errors(self, api, project, plan, override):
        assert make_defect(api, project['id'], plan['id'], **override).status_code == 400

    def test_normalization(self, api, project, plan):
        r = make_defect(api, project['id'], plan['id'], type='Budowlana', type_other='zbędne', description='  opis  ',
                        zoom=9, due_mode='umowa', due_date='2026-12-01').json()
        assert r['type_other'] == '' and r['description'] == 'opis' and r['zoom'] == 0.6 and r['due_date'] is None

    def test_other_type_keeps_clarification(self, api, project, plan):
        r = make_defect(api, project['id'], plan['id'], type='Inna', type_other='Okna').json()
        assert r['type_other'] == 'Okna'

    def test_due_date_mode(self, api, project, plan):
        r = make_defect(api, project['id'], plan['id'], due_mode='data', due_date='2026-12-01').json()
        assert r['due_date'] == '2026-12-01'

    def test_viewer_cannot_create(self, viewer_api, project, plan):
        assert make_defect(viewer_api, project['id'], plan['id']).status_code == 403


def test_plan_must_belong_to_the_same_project(api, project):
    other_plan = make_plan(api, make_project(api, name='Inna')['id'])
    r = post_json(api, f"/api/projects/{project['id']}/defects", defect_body(other_plan['id']))
    assert r.status_code == 400 and 'innej inwestycji' in r.json()['detail']


class TestList:
    def test_filters(self, api, project, plan):
        d1 = make_defect(api, project['id'], plan['id']).json()
        make_defect(api, project['id'], plan['id'])
        add_photo(api, d1['id'], 'after')
        url = f"/api/projects/{project['id']}/defects"
        assert len(api.get(url).json()) == 2
        assert [d['id'] for d in api.get(url, {'status': 'fixed'}).json()] == [d1['id']]
        assert len(api.get(url, {'status': 'open'}).json()) == 1
        assert len(api.get(url, {'status': 'cokolwiek'}).json()) == 2  # nieznany status = brak filtra
        assert len(api.get(url, {'plan_id': plan['id']}).json()) == 2
        assert api.get(url, {'plan_id': str(uuid.uuid4())}).json() == []

    def test_defect_types_come_from_organization(self, api):
        assert 'Budowlana' in api.get('/api/defect-types').json()


class TestUpdate:
    def test_update_logs_only_real_changes(self, api, defect):
        r = patch_json(api, f"/api/defects/{defect['id']}", {'description': 'Nowy opis', 'x': defect['x']})
        assert r.status_code == 200 and r.json()['description'] == 'Nowy opis'
        events = api.get(f"/api/defects/{defect['id']}/events").json()
        assert events[0]['action'] == 'updated' and list(events[0]['changes']) == ['description']

    def test_noop_update_creates_no_event(self, api, defect):
        patch_json(api, f"/api/defects/{defect['id']}", {'description': defect['description']})
        assert DefectEvent.objects.filter(defect_id=defect['id']).count() == 1

    def test_unknown_fields_are_ignored(self, api, defect):
        r = patch_json(api, f"/api/defects/{defect['id']}", {'zoom': 0.4})
        assert r.json()['zoom'] == 0.4

    def test_date_changes_are_serialized_in_history(self, api, defect):
        patch_json(api, f"/api/defects/{defect['id']}", {'due_mode': 'data', 'due_date': '2026-12-24'})
        change = api.get(f"/api/defects/{defect['id']}/events").json()[0]['changes']['due_date']
        assert change == [None, '2026-12-24']

    def test_move_to_another_plan_of_same_project(self, api, project, plan, defect):
        second = make_plan(api, project['id'], 'Piętro')
        r = patch_json(api, f"/api/defects/{defect['id']}", {'plan_id': second['id']})
        assert r.json()['plan_id'] == second['id']

    def test_move_to_plan_of_another_project_is_rejected(self, api, defect):
        foreign = make_plan(api, make_project(api, name='Inna')['id'])
        r = patch_json(api, f"/api/defects/{defect['id']}", {'plan_id': foreign['id']})
        assert r.status_code == 400

    def test_invalid_update_is_rejected(self, api, defect):
        assert patch_json(api, f"/api/defects/{defect['id']}", {'type': 'Zły'}).status_code == 400

    def test_manually_setting_fixed_date(self, api, defect):
        add_photo(api, defect['id'], 'after')
        r = patch_json(api, f"/api/defects/{defect['id']}", {'fixed_date': '2026-11-20'})
        assert r.json()['fixed_date'] == '2026-11-20'

    def test_fixed_without_date_gets_today(self, api, defect):
        Defect.objects.filter(pk=defect['id']).update(status='fixed', fixed_date=None)
        r = patch_json(api, f"/api/defects/{defect['id']}", {'description': 'x'})
        assert r.json()['fixed_date'] == timezone.localdate().isoformat()

    def test_reopened_defect_loses_fixed_date(self, api, defect):
        Defect.objects.filter(pk=defect['id']).update(fixed_date=dt.date(2026, 1, 1))
        r = patch_json(api, f"/api/defects/{defect['id']}", {'description': 'x'})
        assert r.json()['fixed_date'] is None


class TestPhotosAndStatus:
    def test_after_photo_fixes_defect_and_removal_reopens(self, api, defect):
        r = add_photo(api, defect['id'], 'after')
        assert r.status_code == 201 and r.json()['status'] == 'fixed' and r.json()['fixed_date']
        after_id = next(p['id'] for p in r.json()['photos'] if p['kind'] == 'after')
        reopened = api.delete(f'/api/photos/{after_id}')
        assert reopened.json()['status'] == 'open' and reopened.json()['fixed_date'] is None
        actions = [e['action'] for e in api.get(f"/api/defects/{defect['id']}/events").json()]
        assert actions.count('status') == 2 and 'photo_added' in actions and 'photo_removed' in actions

    def test_second_after_photo_keeps_status_and_orders_photos(self, api, defect):
        add_photo(api, defect['id'], 'after')
        r = add_photo(api, defect['id'], 'after')
        assert r.json()['status'] == 'fixed'
        assert sorted(Photo.objects.filter(defect_id=defect['id']).values_list('order', flat=True)) == [1, 2]

    def test_before_photo_does_not_change_status(self, api, defect):
        assert add_photo(api, defect['id'], 'before').json()['status'] == 'open'

    def test_unknown_kind_is_rejected(self, api, defect):
        assert api.post(f"/api/defects/{defect['id']}/photos", {'kind': 'x', 'file': jpeg()}).status_code == 400

    def test_download_photo(self, api, defect):
        pid = add_photo(api, defect['id']).json()['photos'][0]['id']
        assert api.get(f'/api/photos/{pid}/file').status_code == 200

    def test_photo_of_another_org_is_hidden(self, api, other_api, defect):
        pid = add_photo(api, defect['id']).json()['photos'][0]['id']
        assert other_api.get(f'/api/photos/{pid}/file').status_code == 404
        assert other_api.delete(f'/api/photos/{pid}').status_code == 404

    def test_viewer_cannot_delete_photo(self, api, viewer_api, defect):
        pid = add_photo(api, defect['id']).json()['photos'][0]['id']
        assert viewer_api.delete(f'/api/photos/{pid}').status_code == 403


class TestDelete:
    def test_delete_removes_photos_files_and_record(self, api, defect, settings):
        add_photo(api, defect['id'])
        assert any(settings.MEDIA_ROOT.rglob('photos/*'))
        assert api.delete(f"/api/defects/{defect['id']}").status_code == 204
        assert not Defect.objects.exists() and not any(settings.MEDIA_ROOT.rglob('photos/*'))

    def test_isolated_between_orgs(self, other_api, defect):
        assert other_api.get(f"/api/defects/{defect['id']}").status_code == 404
        assert other_api.delete(f"/api/defects/{defect['id']}").status_code == 404

    def test_viewer_cannot_delete(self, viewer_api, defect):
        assert viewer_api.delete(f"/api/defects/{defect['id']}").status_code == 403


def test_string_representations(defect, api):
    add_photo(api, defect['id'])
    d = Defect.objects.get(pk=defect['id'])
    assert str(d) == 'Usterka nr 1'
    assert 'Przed' in str(Photo.objects.get())
    assert str(DefectEvent.objects.first()) == 'Usterka nr 1: photo_added'


def test_event_without_user_has_empty_author(api, defect):
    DefectEvent.objects.filter(defect_id=defect['id']).update(user=None)
    assert api.get(f"/api/defects/{defect['id']}/events").json()[0]['user'] == ''
