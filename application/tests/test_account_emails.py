"""Reset hasła, potwierdzanie adresu e-mail, unieważnianie sesji po zmianie hasła."""

import re

import pytest
from django.core import mail, signing
from django.test import Client, override_settings

from core.auth import make_password_token
from tests.helpers import PASSWORD, post_json
from users import emails
from users.models import User

pytestmark = pytest.mark.django_db

NEW_PASSWORD = 'Zupelnie-nowe-haslo-7'


def bearer(token) -> Client:
    return Client(headers={'Authorization': f'Bearer {token}'})


@pytest.fixture
def account(client):
    """Konto założone przez rejestrację (ma własne hasło, adres niepotwierdzony)."""
    r = post_json(client, '/api/auth/register', {'email': 'ola@firma.pl', 'password': PASSWORD, 'name': 'Ola'})
    mail.outbox.clear()
    return {'token': r.json()['token'], 'user': User.objects.get(email='ola@firma.pl')}


def link_params(message) -> dict:
    url = re.search(r'https?://\S+', message.body).group(0)
    return dict(p.split('=', 1) for p in url.split('?', 1)[1].split('&'))


def request_reset(client, email='ola@firma.pl'):
    return post_json(client, '/api/auth/password-reset', {'email': email})


def confirm(client, params, password=NEW_PASSWORD):
    return post_json(client, '/api/auth/password-reset/confirm', {**params, 'password': password})


class TestEmailVerification:
    def test_registration_sends_verification_link(self, client):
        r = post_json(client, '/api/auth/register', {'email': 'ola@firma.pl', 'password': PASSWORD})
        assert r.status_code == 201 and len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == ['ola@firma.pl'] and '/verify-email?token=' in message.body

    def test_new_account_is_unverified_and_link_verifies_it(self, client, account):
        assert bearer(account['token']).get('/api/auth/me').json()['email_verified'] is False
        token = emails.verification_token(account['user'])
        assert post_json(client, '/api/auth/verify-email', {'token': token}).json() == {'ok': True}
        assert bearer(account['token']).get('/api/auth/me').json()['email_verified'] is True

    def test_verifying_twice_is_harmless(self, client, account):
        token = emails.verification_token(account['user'])
        assert post_json(client, '/api/auth/verify-email', {'token': token}).status_code == 200
        assert post_json(client, '/api/auth/verify-email', {'token': token}).status_code == 200

    @pytest.mark.parametrize('token', ['smiec', ''])
    def test_garbage_token(self, client, token):
        assert post_json(client, '/api/auth/verify-email', {'token': token}).status_code == 400

    def test_expired_link(self, client, account):
        token = emails.verification_token(account['user'])
        with override_settings(EMAIL_VERIFY_MAX_AGE=-1):
            assert post_json(client, '/api/auth/verify-email', {'token': token}).status_code == 400

    def test_link_for_changed_or_deleted_account(self, client, account):
        token = emails.verification_token(account['user'])
        User.objects.filter(pk=account['user'].pk).update(email='inny@firma.pl')
        assert post_json(client, '/api/auth/verify-email', {'token': token}).status_code == 400

    def test_token_for_another_purpose_is_rejected(self, client, account):
        forged = signing.dumps({'uid': account['user'].pk, 'email': 'ola@firma.pl'}, salt='inny-cel')
        assert post_json(client, '/api/auth/verify-email', {'token': forged}).status_code == 400

    def test_resend(self, account):
        r = bearer(account['token']).post('/api/auth/resend-verification')
        assert r.status_code == 200 and len(mail.outbox) == 1

    def test_resend_for_verified_account_is_rejected(self, api):
        assert api.post('/api/auth/resend-verification').status_code == 400

    def test_resend_reports_mail_failure(self, account, settings):
        settings.EMAIL_BACKEND = 'tests.test_account_emails.BrokenBackend'
        assert bearer(account['token']).post('/api/auth/resend-verification').status_code == 503

    def test_resend_is_rate_limited(self, account):
        codes = [bearer(account['token']).post('/api/auth/resend-verification').status_code for _ in range(6)]
        assert codes[:5] == [200] * 5 and codes[5] == 429

    def test_dev_and_microsoft_accounts_start_verified(self, api, monkeypatch):
        assert api.get('/api/auth/me').json()['email_verified'] is True
        monkeypatch.setattr('core.entra.validate_token', lambda t: {'oid': 'o', 'tid': 't', 'preferred_username': 'ms@firma.pl'})
        assert bearer('microsoft').get('/api/auth/me').json()['email_verified'] is True

    def test_registration_survives_mail_failure(self, client, settings):
        settings.EMAIL_BACKEND = 'tests.test_account_emails.BrokenBackend'
        assert post_json(client, '/api/auth/register', {'email': 'ola@firma.pl', 'password': PASSWORD}).status_code == 201

    def test_unverified_admin_cannot_buy_a_plan(self, account, settings):
        settings.DEBUG, settings.STRIPE_SECRET_KEY = True, ''
        r = post_json(bearer(account['token']), '/api/billing/checkout', {'plan': 'pro'})
        assert r.status_code == 403 and 'Potwierdź adres' in r.json()['detail']


class BrokenBackend:
    """Backend poczty, który zawsze zawodzi (symulacja niedostępnego SMTP)."""

    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise ConnectionRefusedError('smtp niedostępny')


class TestPasswordReset:
    def test_full_flow(self, client, account):
        assert request_reset(client).json() == {'ok': True}
        assert len(mail.outbox) == 1 and 'reset-password?uid=' in mail.outbox[0].body

        r = confirm(client, link_params(mail.outbox[0]))
        assert r.status_code == 200
        assert bearer(r.json()['token']).get('/api/auth/me').status_code == 200  # od razu zalogowany
        assert post_json(client, '/api/auth/login', {'email': 'ola@firma.pl', 'password': NEW_PASSWORD}).status_code == 200
        assert post_json(client, '/api/auth/login', {'email': 'ola@firma.pl', 'password': PASSWORD}).status_code == 401

    def test_link_works_only_once(self, client, account):
        request_reset(client)
        params = link_params(mail.outbox[0])
        assert confirm(client, params).status_code == 200
        assert confirm(client, params, 'Jeszcze-inne-haslo-9').status_code == 400

    def test_reset_signs_out_old_sessions(self, client, account):
        request_reset(client)
        confirm(client, link_params(mail.outbox[0]))
        assert bearer(account['token']).get('/api/auth/me').status_code == 401

    def test_reset_verifies_email_and_clears_lockout(self, client, account):
        for _ in range(5):
            post_json(client, '/api/auth/login', {'email': 'ola@firma.pl', 'password': 'zle'})
        request_reset(client)
        confirm(client, link_params(mail.outbox[0]))
        assert User.objects.get(email='ola@firma.pl').email_verified
        assert post_json(client, '/api/auth/login', {'email': 'ola@firma.pl', 'password': NEW_PASSWORD}).status_code == 200

    @pytest.mark.parametrize('email', ['nikt@nigdzie.pl', 'OLA@firma.pl'])
    def test_no_account_enumeration(self, client, account, email):
        assert request_reset(client, email).json() == {'ok': True}

    def test_unknown_email_sends_nothing(self, client, account):
        request_reset(client, 'nikt@nigdzie.pl')
        assert mail.outbox == []

    def test_email_matching_is_case_insensitive(self, client, account):
        request_reset(client, 'OLA@FIRMA.PL')
        assert len(mail.outbox) == 1

    def test_accounts_without_own_password_get_no_mail(self, client, user):
        request_reset(client, 'jan.kowalski@firma.pl')  # konto dev: brak hasła do zresetowania
        assert mail.outbox == []

    def test_microsoft_accounts_get_no_mail(self, client, account):
        User.objects.filter(pk=account['user'].pk).update(entra_oid='abc')
        request_reset(client)
        assert mail.outbox == []

    def test_inactive_accounts_get_no_mail(self, client, account):
        User.objects.filter(pk=account['user'].pk).update(is_active=False)
        request_reset(client)
        assert mail.outbox == []

    def test_requests_are_rate_limited_per_email(self, client, account):
        codes = [request_reset(client).status_code for _ in range(6)]
        assert codes[:5] == [200] * 5 and codes[5] == 429

    def test_requests_are_rate_limited_per_ip(self, client):
        codes = [request_reset(client, f'x{i}@firma.pl').status_code for i in range(21)]
        assert codes[:20] == [200] * 20 and codes[20] == 429

    @pytest.mark.parametrize('uid, token', [('!!!', 'x'), ('MQ', 'zly-token'), ('OTk5OTk5', 'x'), ('', '')])
    def test_invalid_links(self, client, account, uid, token):
        assert confirm(client, {'uid': uid, 'token': token}).status_code == 400

    def test_expired_link(self, client, account):
        request_reset(client)
        params = link_params(mail.outbox[0])
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            assert confirm(client, params).status_code == 400

    @pytest.mark.parametrize('password', ['123', 'a' * 129, 'ola'])
    def test_weak_new_password_is_rejected_and_link_survives(self, client, account, password):
        request_reset(client)
        params = link_params(mail.outbox[0])
        assert confirm(client, params, password).status_code == 400
        assert confirm(client, params).status_code == 200

    def test_mail_failure_is_not_revealed(self, client, account, settings):
        settings.EMAIL_BACKEND = 'tests.test_account_emails.BrokenBackend'
        assert request_reset(client).status_code == 200

    def test_disabled_password_login(self, client):
        with override_settings(AUTH_PASSWORD_LOGIN=False):
            assert request_reset(client).status_code == 404
            assert confirm(client, {'uid': 'a', 'token': 'b'}).status_code == 404


class TestSessionInvalidation:
    def test_token_dies_after_password_change(self, user):
        token = make_password_token(user.pk)
        assert bearer(token).get('/api/auth/me').status_code == 200
        user.set_password('Nowe-haslo-12345')
        user.save()
        assert bearer(token).get('/api/auth/me').status_code == 401

    def test_old_format_token_without_fingerprint_is_rejected(self, user):
        from core.auth import PWD_PREFIX, PWD_SALT

        legacy = PWD_PREFIX + signing.dumps({'uid': user.pk}, salt=PWD_SALT)
        assert bearer(legacy).get('/api/auth/me').status_code == 401


def test_frontend_link_builder(settings):
    from core.mail import frontend_link

    settings.FRONTEND_URL = 'https://x.pl/'
    assert frontend_link('/a', q='1 2') == 'https://x.pl/a?q=1+2' and frontend_link('/b') == 'https://x.pl/b'


def test_send_text_reports_failure(settings, caplog):
    from core.mail import send_text

    settings.EMAIL_BACKEND = 'tests.test_account_emails.BrokenBackend'
    with caplog.at_level('ERROR'):
        assert send_text('a@b.pl', 'Temat', 'Treść') is False
    assert 'Nie udało się wysłać e-maila' in caplog.text
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    assert send_text('a@b.pl', 'Temat', 'Treść') is True and mail.outbox[-1].subject == 'Temat'


def test_sender_address_comes_from_settings(client, settings):
    settings.DEFAULT_FROM_EMAIL = 'Usterki <noreply@axword.pl>'
    post_json(client, '/api/auth/register', {'email': 'ola@firma.pl', 'password': PASSWORD})
    assert mail.outbox[0].from_email == 'Usterki <noreply@axword.pl>'
