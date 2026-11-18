"""Logowanie: hasło, tryb dev, Microsoft (token), blokady i konfiguracja."""

import pytest
from django.core import signing
from django.test import Client, override_settings

from core.auth import DEV_PREFIX, DEV_SALT, PWD_PREFIX, PWD_SALT, make_dev_token, make_password_token
from core.entra import EntraTokenError
from organizations.models import Membership, Organization
from tests.helpers import PASSWORD, post_json
from users.models import User

pytestmark = pytest.mark.django_db


def register(client, email='ola@firma.pl', **extra):
    return post_json(client, '/api/auth/register', {'email': email, 'password': PASSWORD, **extra})


def login(client, email='ola@firma.pl', password=PASSWORD):
    return post_json(client, '/api/auth/login', {'email': email, 'password': password})


def bearer(token) -> Client:
    return Client(headers={'Authorization': f'Bearer {token}'})


class TestConfig:
    def test_public_config(self, client):
        data = client.get('/api/auth/config').json()
        assert data['password_login'] is True and data['dev_login'] is True and data['microsoft'] is True

    def test_api_requires_token(self, client):
        assert client.get('/api/projects/').status_code == 401


class TestRegistration:
    def test_register_creates_admin_of_new_organization(self, client):
        r = register(client, name='Ola', company='Budowa SA')
        assert r.status_code == 201
        me = bearer(r.json()['token']).get('/api/auth/me').json()
        assert (me['email'], me['role'], me['organization_name']) == ('ola@firma.pl', 'admin', 'Budowa SA')
        assert me['microsoft'] is False

    def test_email_is_normalized_and_name_defaults(self, client):
        token = register(client, 'Ola@Firma.PL').json()['token']
        me = bearer(token).get('/api/auth/me').json()
        assert me['email'] == 'ola@firma.pl' and me['display_name'] == 'ola'
        assert me['organization_name'] == 'Firma ola'

    def test_duplicate_email_is_rejected(self, client):
        register(client)
        assert register(client).status_code == 409

    @pytest.mark.parametrize('password', ['123', 'haslo', 'a' * 129, 'janinanowak@firma.pl', 'janinanowak'])
    def test_weak_or_oversized_passwords_are_rejected(self, client, password):
        r = post_json(client, '/api/auth/register', {'email': 'janinanowak@firma.pl', 'password': password})
        assert r.status_code == 400

    def test_same_domain_does_not_join_existing_organization(self, client):
        a = bearer(register(client, 'a@wspolna.pl').json()['token']).get('/api/auth/me').json()
        b = bearer(register(client, 'b@wspolna.pl').json()['token']).get('/api/auth/me').json()
        assert a['organization_id'] != b['organization_id']

    def test_signup_is_rate_limited_per_ip(self, client):
        codes = [register(client, f'u{i}@firma.pl').status_code for i in range(11)]
        assert codes[:10] == [201] * 10 and codes[10] == 429

    def test_disabled_password_login(self, client):
        with override_settings(AUTH_PASSWORD_LOGIN=False):
            assert register(client).status_code == 404
            assert login(client).status_code == 404


class TestPasswordLogin:
    def test_success_and_failure(self, client):
        register(client)
        assert login(client).status_code == 200
        wrong = login(client, password='zle-haslo')
        assert wrong.status_code == 401 and wrong.json()['detail'] == 'Nieprawidłowy e-mail lub hasło.'

    def test_unknown_account_gives_identical_error(self, client):
        r = login(client, 'nikt@nigdzie.pl', 'cokolwiek')
        assert r.status_code == 401 and r.json()['detail'] == 'Nieprawidłowy e-mail lub hasło.'

    def test_overlong_password_is_not_hashed(self, client):
        register(client)
        assert login(client, password='a' * 5000).status_code == 401

    def test_inactive_user_cannot_log_in(self, client):
        register(client)
        User.objects.update(is_active=False)
        assert login(client).status_code == 401

    def test_lockout_after_five_failures_even_with_correct_password(self, client):
        register(client)
        assert [login(client, password='zle').status_code for _ in range(5)] == [401] * 5
        assert login(client).status_code == 429

    def test_success_resets_the_counter(self, client):
        register(client)
        for _ in range(4):
            login(client, password='zle')
        assert login(client).status_code == 200
        assert login(client, password='zle').status_code == 401  # licznik wyzerowany, nie 429

    def test_ip_wide_lockout_hits_other_accounts(self, client):
        register(client)
        for i in range(20):
            login(client, f'x{i}@firma.pl', 'zle')
        assert login(client).status_code == 429

    def test_lockout_is_per_email(self, client):
        register(client)
        register(client, 'inna@firma.pl')
        for _ in range(5):
            login(client, password='zle')
        other_ip = Client(headers={'X-Forwarded-For': '203.0.113.9'})
        assert login(other_ip, 'inna@firma.pl').status_code == 200  # inny adres, inne konto


class TestTokens:
    def test_password_token_roundtrip(self, user):
        assert bearer(make_password_token(user.pk)).get('/api/auth/me').status_code == 200

    @pytest.mark.parametrize('token', [DEV_PREFIX + 'smiec', PWD_PREFIX + 'smiec'])
    def test_tampered_tokens_are_rejected(self, token):
        r = bearer(token).get('/api/auth/me')
        assert r.status_code == 401 and 'wygasła' in r.json()['detail']

    def test_token_signed_for_another_purpose_is_rejected(self, user):
        forged = PWD_PREFIX + signing.dumps({'uid': user.pk}, salt=DEV_SALT)
        assert bearer(forged).get('/api/auth/me').status_code == 401

    def test_expired_token_is_rejected(self, user):
        token = make_password_token(user.pk)
        with override_settings(PASSWORD_TOKEN_MAX_AGE=-1):
            assert bearer(token).get('/api/auth/me').status_code == 401

    def test_inactive_user_token_stops_working(self, user):
        token = make_password_token(user.pk)
        User.objects.filter(pk=user.pk).update(is_active=False)
        r = bearer(token).get('/api/auth/me')
        assert r.status_code == 401 and r.json()['detail'] == 'Nieznany użytkownik.'

    def test_dev_token_when_dev_login_disabled(self, user):
        with override_settings(AUTH_DEV_LOGIN=False):
            assert bearer(make_dev_token(user.pk)).get('/api/auth/me').status_code == 401

    def test_password_token_when_password_login_disabled(self, user):
        with override_settings(AUTH_PASSWORD_LOGIN=False):
            assert bearer(make_password_token(user.pk)).get('/api/auth/me').status_code == 401

    def test_salts_differ(self):
        assert DEV_SALT != PWD_SALT


class TestDevLogin:
    def test_dev_login_groups_people_by_domain(self, client):
        t1 = post_json(client, '/api/auth/dev-login', {'email': 'a@firma.pl'}).json()['token']
        t2 = post_json(client, '/api/auth/dev-login', {'email': 'b@firma.pl', 'name': 'Bartek'}).json()['token']
        a, b = (bearer(t).get('/api/auth/me').json() for t in (t1, t2))
        assert (a['role'], b['role']) == ('admin', 'inspector') and a['organization_id'] == b['organization_id']

    def test_dev_login_reuses_existing_user(self, client):
        post_json(client, '/api/auth/dev-login', {'email': 'a@firma.pl'})
        post_json(client, '/api/auth/dev-login', {'email': 'a@firma.pl'})
        assert User.objects.filter(email='a@firma.pl').count() == 1

    def test_dev_login_disabled(self, client):
        with override_settings(AUTH_DEV_LOGIN=False):
            assert post_json(client, '/api/auth/dev-login', {'email': 'a@firma.pl'}).status_code == 404


class TestMicrosoftToken:
    CLAIMS = {'oid': 'oid-1', 'tid': 'tenant-1', 'preferred_username': 'Ewa@Firma.pl', 'name': 'Ewa'}

    def test_valid_microsoft_token_creates_user_and_organization(self, client, monkeypatch):
        monkeypatch.setattr('core.entra.validate_token', lambda token: self.CLAIMS)
        r = Client(headers={'Authorization': 'Bearer microsoft-token'}).get('/api/auth/me')
        me = r.json()
        assert r.status_code == 200 and me['microsoft'] is True and me['role'] == 'admin' and me['email'] == 'ewa@firma.pl'

    def test_invalid_microsoft_token(self, monkeypatch):
        def boom(token):
            raise EntraTokenError('zły token')

        monkeypatch.setattr('core.entra.validate_token', boom)
        r = bearer('x').get('/api/auth/me')
        assert r.status_code == 401 and r.json()['detail'] == 'zły token'

    def test_microsoft_token_is_kept_for_sharepoint(self, monkeypatch, rf):
        from core.auth import ApiAuth

        monkeypatch.setattr('core.entra.validate_token', lambda token: self.CLAIMS)
        request = rf.get('/')
        ApiAuth().authenticate(request, 'tok')
        assert request.ms_token == 'tok'


class TestEntraProvisioning:
    def claims(self, **kw):
        return {'oid': 'oid-1', 'tid': 'tenant-1', 'preferred_username': 'ewa@firma.pl', 'name': 'Ewa', **kw}

    def test_second_person_from_known_tenant_joins_as_inspector(self):
        from users.services import user_from_entra_claims

        user_from_entra_claims(self.claims())
        second = user_from_entra_claims(self.claims(oid='oid-2', preferred_username='adam@firma.pl'))
        assert Membership.objects.get(user=second).role == 'inspector' and Organization.objects.count() == 1

    def test_signup_of_unknown_tenant_can_be_disabled(self):
        from ninja.errors import HttpError

        from users.services import user_from_entra_claims

        with override_settings(ENTRA_ALLOW_ORG_SIGNUP=False), pytest.raises(HttpError) as exc:
            user_from_entra_claims(self.claims())
        assert exc.value.status_code == 403

    def test_blocked_account_is_rejected(self):
        from ninja.errors import HttpError

        from users.services import user_from_entra_claims

        user_from_entra_claims(self.claims())
        User.objects.update(is_active=False)
        with pytest.raises(HttpError):
            user_from_entra_claims(self.claims())

    def test_existing_local_account_is_linked_by_email(self):
        from users.services import user_from_entra_claims

        local = User.objects.create_user(username='ewa@firma.pl', email='ewa@firma.pl')
        assert user_from_entra_claims(self.claims()).pk == local.pk
        local.refresh_from_db()
        assert local.entra_oid == 'oid-1'

    def test_changed_name_and_email_are_synced(self):
        from users.services import user_from_entra_claims

        user_from_entra_claims(self.claims())
        user = user_from_entra_claims(self.claims(preferred_username='ewa.nowa@firma.pl', name='Ewa Nowa'))
        assert (user.email, user.display_name) == ('ewa.nowa@firma.pl', 'Ewa Nowa')

    def test_unchanged_claims_cause_no_update(self):
        from users.services import user_from_entra_claims

        first = user_from_entra_claims(self.claims())
        assert user_from_entra_claims(self.claims()).pk == first.pk

    @pytest.mark.parametrize('claims, expected', [
        ({'preferred_username': 'A@B.pl', 'oid': 'o'}, 'a@b.pl'),
        ({'upn': 'U@B.pl', 'oid': 'o'}, 'u@b.pl'),
        ({'email': 'E@B.pl', 'oid': 'o'}, 'e@b.pl'),
        ({'oid': 'o'}, 'o@entra.local'),
    ])
    def test_email_fallbacks(self, claims, expected):
        from users.services import _email_from_claims

        assert _email_from_claims(claims) == expected


def test_user_str(user):
    assert str(user) == 'Jan Kowalski'
    assert str(User(email='a@b.pl')) == 'a@b.pl'


def test_password_salt_constant_is_used_by_tokens(user):
    token = make_password_token(user.pk)
    assert signing.loads(token[len(PWD_PREFIX):], salt=PWD_SALT)['uid'] == user.pk
