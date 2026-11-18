"""Wspólne fixtures. Każdy test dostaje czystą bazę, pusty cache i własny katalog plików."""

import pytest
from django.core.cache import cache
from django.test import Client

from billing.services import activate_demo
from core.auth import make_dev_token
from organizations.models import Membership
from tests.helpers import make_plan, make_project
from users.services import dev_login


@pytest.fixture(autouse=True)
def _clean_state(settings, tmp_path):
    """Izolacja: licznik prób logowania i pliki nie przeciekają między testami."""
    settings.MEDIA_ROOT = tmp_path / 'media'
    cache.clear()


def client_for(user) -> Client:
    return Client(headers={'Authorization': f'Bearer {make_dev_token(user.pk)}'})


@pytest.fixture
def user(db):
    """Administrator organizacji firma.pl (pierwsza osoba z domeny)."""
    return dev_login('jan.kowalski@firma.pl', 'Jan Kowalski')


@pytest.fixture
def org(user):
    return Membership.objects.get(user=user).organization


@pytest.fixture
def api(user):
    return client_for(user)


@pytest.fixture
def other_api(db):
    """Użytkownik z innej organizacji - do testów izolacji."""
    return client_for(dev_login('obcy@inna.pl'))


@pytest.fixture
def inspector(user):
    """Druga osoba z firma.pl: rola inspector."""
    return dev_login('anna.nowak@firma.pl', 'Anna Nowak')


@pytest.fixture
def viewer_api(user):
    """Osoba z firma.pl z rolą tylko do podglądu."""
    u = dev_login('widz@firma.pl')
    Membership.objects.filter(user=u).update(role='viewer')
    return client_for(u)


@pytest.fixture
def pro(org):
    """Organizacja z planem Pro (plan Start pozwala na jedną inwestycję)."""
    activate_demo(org, 'pro')


@pytest.fixture
def project(api, pro):
    return make_project(api)


@pytest.fixture
def plan(api, project):
    return make_plan(api, project['id'])
