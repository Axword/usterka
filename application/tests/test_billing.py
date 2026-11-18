# ruff: noqa: E501
import json

import pytest
from django.test import Client, override_settings

from core.auth import make_password_token
from tests.test_api import make_project


def post(c, url, body):
    return c.post(url, json.dumps(body), content_type='application/json')


@pytest.mark.django_db
def test_register_login_and_me(client):
    r = post(client, '/api/auth/register', {'email': 'Ola@Firma.PL', 'password': 'Dobre-haslo-123', 'name': 'Ola', 'company': 'Budowa SA'})
    assert r.status_code == 201
    c = Client(headers={'Authorization': f"Bearer {r.json()['token']}"})
    me = c.get('/api/auth/me').json()
    assert me['email'] == 'ola@firma.pl' and me['role'] == 'admin' and me['organization_name'] == 'Budowa SA'
    assert post(client, '/api/auth/register', {'email': 'ola@firma.pl', 'password': 'Dobre-haslo-123'}).status_code == 409
    assert post(client, '/api/auth/login', {'email': 'ola@firma.pl', 'password': 'zle'}).status_code == 401
    assert post(client, '/api/auth/login', {'email': 'ola@firma.pl', 'password': 'Dobre-haslo-123'}).status_code == 200


@pytest.mark.django_db
def test_weak_password_rejected(client):
    assert post(client, '/api/auth/register', {'email': 'a@b.pl', 'password': '123'}).status_code == 400


@pytest.mark.django_db
def test_password_registrations_are_isolated(client):
    t1 = post(client, '/api/auth/register', {'email': 'a@same.pl', 'password': 'Dobre-haslo-123'}).json()['token']
    t2 = post(client, '/api/auth/register', {'email': 'b@same.pl', 'password': 'Dobre-haslo-123'}).json()['token']
    c1, c2 = (Client(headers={'Authorization': f'Bearer {t}'}) for t in (t1, t2))
    assert c1.get('/api/auth/me').json()['organization_id'] != c2.get('/api/auth/me').json()['organization_id']


@pytest.mark.django_db
def test_password_login_can_be_disabled(user):
    with override_settings(AUTH_PASSWORD_LOGIN=False):
        c = Client(headers={'Authorization': f'Bearer {make_password_token(user.pk)}'})
        assert c.get('/api/auth/me').status_code == 401
        assert post(c, '/api/auth/login', {'email': 'a@b.pl', 'password': 'x'}).status_code == 404


@pytest.mark.django_db
@override_settings(DEBUG=True, STRIPE_SECRET_KEY='')
def test_free_plan_limit_and_demo_upgrade(api):
    make_project(api)
    r = api.post('/api/projects/', {'name': 'Druga'}, content_type='application/json')
    assert r.status_code == 402
    assert post(api, '/api/billing/checkout', {'plan': 'pro'}).json()['activated'] is True
    assert api.get('/api/billing/subscription').json()['plan'] == 'pro'
    assert api.post('/api/projects/', {'name': 'Druga'}, content_type='application/json').status_code == 201
    assert post(api, '/api/billing/downgrade', {}).json()['plan'] == 'free'


@pytest.mark.django_db
@override_settings(DEBUG=False, STRIPE_SECRET_KEY='')
def test_checkout_unavailable_without_stripe_in_production(api):
    assert post(api, '/api/billing/checkout', {'plan': 'pro'}).status_code == 503


@pytest.mark.django_db
def test_plans_public_and_webhook_requires_signature(client):
    assert client.get('/api/billing/plans').status_code == 200
    assert client.post('/api/billing/webhook', b'{}', content_type='application/json').status_code == 400


@pytest.mark.django_db
def test_webhook_events_update_subscription(user):
    from billing.models import Subscription
    from billing.services import handle_event
    from organizations.models import Membership

    org = Membership.objects.get(user=user).organization
    Subscription.objects.create(organization=org)
    with override_settings(STRIPE_PRICE_PRO='price_pro', STRIPE_PRICE_BUSINESS='price_biz'):
        handle_event({'type': 'checkout.session.completed', 'data': {'object': {
            'mode': 'subscription', 'client_reference_id': str(org.pk), 'customer': 'cus_1', 'subscription': 'sub_1', 'metadata': {'plan': 'pro'}}}})
        sub = Subscription.objects.get(organization=org)
        assert (sub.plan, sub.status, sub.stripe_customer_id) == ('pro', 'active', 'cus_1')
        handle_event({'type': 'customer.subscription.updated', 'data': {'object': {
            'id': 'sub_1', 'customer': 'cus_1', 'status': 'active', 'cancel_at_period_end': True,
            'items': {'data': [{'price': {'id': 'price_biz'}, 'current_period_end': 1893456000}]}}}})
        sub.refresh_from_db()
        assert sub.plan == 'business' and sub.cancel_at_period_end and sub.current_period_end
        handle_event({'type': 'customer.subscription.deleted', 'data': {'object': {'id': 'sub_1', 'customer': 'cus_1', 'status': 'canceled', 'items': {'data': []}}}})
        sub.refresh_from_db()
        assert sub.status == 'canceled' and sub.effective_plan == 'free'


@pytest.mark.django_db
def test_lockout_after_failed_attempts(client):
    post(client, '/api/auth/register', {'email': 'lock@firma.pl', 'password': 'Dobre-haslo-123'})
    for _ in range(5):
        assert post(client, '/api/auth/login', {'email': 'lock@firma.pl', 'password': 'zle'}).status_code == 401
    # po 5 błędach blokada działa nawet z poprawnym hasłem
    assert post(client, '/api/auth/login', {'email': 'lock@firma.pl', 'password': 'Dobre-haslo-123'}).status_code == 429


@pytest.mark.django_db
def test_success_resets_failure_counter(client):
    post(client, '/api/auth/register', {'email': 'ok@firma.pl', 'password': 'Dobre-haslo-123'})
    for _ in range(4):
        post(client, '/api/auth/login', {'email': 'ok@firma.pl', 'password': 'zle'})
    assert post(client, '/api/auth/login', {'email': 'ok@firma.pl', 'password': 'Dobre-haslo-123'}).status_code == 200
    assert post(client, '/api/auth/login', {'email': 'ok@firma.pl', 'password': 'zle'}).status_code == 401


@pytest.mark.django_db
def test_unknown_email_also_counts_and_gives_same_error(client):
    r = post(client, '/api/auth/login', {'email': 'nikt@nigdzie.pl', 'password': 'cokolwiek'})
    assert r.status_code == 401 and r.json()['detail'] == 'Nieprawidłowy e-mail lub hasło.'


@pytest.mark.django_db
def test_very_long_password_rejected(client):
    assert post(client, '/api/auth/register', {'email': 'x@y.pl', 'password': 'a1' * 100}).status_code == 400


@pytest.mark.django_db
def test_password_similar_to_email_rejected(client):
    assert post(client, '/api/auth/register', {'email': 'janinanowak@firma.pl', 'password': 'janinanowak'}).status_code == 400


def test_argon2_is_primary_hasher():
    from django.conf import settings
    from django.contrib.auth.hashers import make_password

    with override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.Argon2PasswordHasher']):
        assert make_password('Dobre-haslo-123').startswith('argon2$argon2id$')
    from config.settings import base
    assert base.PASSWORD_HASHERS[0].endswith('Argon2PasswordHasher')
    assert settings.AUTH_PASSWORD_LOGIN
