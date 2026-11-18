import pytest

from organizations.models import Membership
from tests.helpers import patch_json

pytestmark = pytest.mark.django_db

SITE = 'https://firma.sharepoint.com/sites/Odbiory'


def test_read_organization(api):
    data = api.get('/api/organization/').json()
    assert data['name'] == 'firma.pl' and data['sharepoint_configured'] is False
    assert 'Budowlana' in data['defect_types']


def test_admin_updates_settings(api):
    r = patch_json(api, '/api/organization/', {'name': '  Moja Firma  ', 'sp_site_url': SITE + '/', 'sp_library': 'Dokumenty',
                                                'sp_folder': 'Usterki/{inwestycja}'})
    data = r.json()
    assert data['name'] == 'Moja Firma' and data['sp_site_url'] == SITE and data['sharepoint_configured'] is True


def test_clearing_sharepoint_address_is_allowed(api):
    patch_json(api, '/api/organization/', {'sp_site_url': SITE})
    assert patch_json(api, '/api/organization/', {'sp_site_url': ''}).json()['sp_site_url'] == ''


@pytest.mark.parametrize('url', ['http://firma.sharepoint.com/sites/x', 'https://example.com/sites/x', 'sharepoint', 'https://a.sharepoint.com/'])
def test_invalid_sharepoint_address(api, url):
    assert patch_json(api, '/api/organization/', {'sp_site_url': url}).status_code == 400


def test_defect_types_are_trimmed_and_deduplicated(api):
    r = patch_json(api, '/api/organization/', {'defect_types': [' Dach ', 'Dach', '', 'Okna']})
    assert r.json()['defect_types'] == ['Dach', 'Okna']


def test_at_least_one_defect_type_is_required(api):
    assert patch_json(api, '/api/organization/', {'defect_types': ['  ', '']}).status_code == 400


def test_non_admin_cannot_change_settings(viewer_api):
    assert patch_json(viewer_api, '/api/organization/', {'name': 'Zmiana'}).status_code == 403
    assert viewer_api.get('/api/organization/').status_code == 200


def test_members_list_is_sorted_and_scoped(api, inspector, other_api):
    emails = [m['email'] for m in api.get('/api/organization/members').json()]
    assert emails == ['anna.nowak@firma.pl', 'jan.kowalski@firma.pl']
    assert [m['email'] for m in other_api.get('/api/organization/members').json()] == ['obcy@inna.pl']


def test_admin_changes_role(api, inspector):
    member = Membership.objects.get(user=inspector)
    r = patch_json(api, f'/api/organization/members/{member.pk}', {'role': 'viewer'})
    assert r.status_code == 200 and r.json()['role'] == 'viewer'


def test_unknown_role_is_rejected(api, inspector):
    member = Membership.objects.get(user=inspector)
    assert patch_json(api, f'/api/organization/members/{member.pk}', {'role': 'szef'}).status_code == 400


def test_admin_cannot_demote_self(api, user):
    member = Membership.objects.get(user=user)
    assert patch_json(api, f'/api/organization/members/{member.pk}', {'role': 'viewer'}).status_code == 400
    assert patch_json(api, f'/api/organization/members/{member.pk}', {'role': 'admin'}).status_code == 200


def test_cannot_change_role_in_other_organization(api, other_api):
    foreign = Membership.objects.get(user__email='obcy@inna.pl')
    assert patch_json(api, f'/api/organization/members/{foreign.pk}', {'role': 'viewer'}).status_code == 404


def test_non_admin_cannot_change_roles(viewer_api, inspector):
    member = Membership.objects.get(user=inspector)
    assert patch_json(viewer_api, f'/api/organization/members/{member.pk}', {'role': 'viewer'}).status_code == 403


def test_string_representations(org, user):
    assert str(org) == 'firma.pl'
    assert str(Membership.objects.get(user=user)) == 'Jan Kowalski @ firma.pl (admin)'
