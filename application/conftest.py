import pytest
from django.test import Client

from core.auth import make_dev_token
from users.services import dev_login


@pytest.fixture
def user(db):
    return dev_login('jan.kowalski@firma.pl', 'Jan Kowalski')


@pytest.fixture
def api(user):
    c = Client(headers={'Authorization': f'Bearer {make_dev_token(user.pk)}'})
    return c


@pytest.fixture
def other_api(db):
    u = dev_login('obcy@inna.pl')
    return Client(headers={'Authorization': f'Bearer {make_dev_token(u.pk)}'})


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    cache.clear()
