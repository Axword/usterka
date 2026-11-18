import datetime as dt
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from django.test import override_settings
from ninja.errors import HttpError

from billing import services
from billing.models import Subscription
from billing.plans import PLANS, demo_mode, plan_for_price, price_id, stripe_configured
from tests.helpers import make_project, post_json

pytestmark = pytest.mark.django_db

STRIPE = {'STRIPE_SECRET_KEY': 'sk_test_x', 'STRIPE_PRICE_PRO': 'price_pro', 'STRIPE_PRICE_BUSINESS': 'price_biz',
          'STRIPE_WEBHOOK_SECRET': 'whsec_test'}


@pytest.fixture
def stripe_on():
    with override_settings(**STRIPE):
        yield


@pytest.fixture
def fake_stripe(monkeypatch):
    calls = {}

    def create_session(**kw):
        calls['checkout'] = kw
        return SimpleNamespace(url='https://checkout.stripe.test/s')

    def create_portal(**kw):
        calls['portal'] = kw
        return SimpleNamespace(url='https://billing.stripe.test/p')

    fake = SimpleNamespace(
        api_key=None,
        checkout=SimpleNamespace(Session=SimpleNamespace(create=create_session)),
        billing_portal=SimpleNamespace(Session=SimpleNamespace(create=create_portal)),
    )
    monkeypatch.setattr(services, 'stripe', fake)
    fake.calls = calls
    return fake


def signed(payload: dict, secret='whsec_test', timestamp=None):
    """Nagłówek Stripe-Signature obliczony tak jak robi to Stripe (HMAC-SHA256 z „t.payload”)."""
    body = json.dumps(payload).encode()
    t = timestamp or int(time.time())
    digest = hmac.new(secret.encode(), f'{t}.'.encode() + body, hashlib.sha256).hexdigest()
    return body, f't={t},v1={digest}'


class TestPlans:
    def test_public_plan_list(self, client):
        data = client.get('/api/billing/plans').json()
        assert [p['id'] for p in data['plans']] == ['free', 'pro', 'business']
        assert data['payments_enabled'] is False

    def test_helpers(self, stripe_on):
        assert stripe_configured() and price_id('pro') == 'price_pro' and price_id('free') == ''
        assert plan_for_price('price_biz') == 'business' and plan_for_price('nieznany') is None and plan_for_price('') is None

    def test_demo_mode_only_in_debug_without_key(self):
        with override_settings(DEBUG=True, STRIPE_SECRET_KEY=''):
            assert demo_mode()
        with override_settings(DEBUG=False, STRIPE_SECRET_KEY=''):
            assert not demo_mode()
        with override_settings(DEBUG=True, STRIPE_SECRET_KEY='sk'):
            assert not demo_mode()


class TestLimits:
    def test_free_plan_allows_one_project(self, api):
        make_project(api)
        r = post_json(api, '/api/projects/', {'name': 'Druga'})
        assert r.status_code == 402 and '1 inwestycji' in r.json()['detail']

    def test_pro_allows_ten_and_business_is_unlimited(self, api, org):
        services.activate_demo(org, 'pro')
        for i in range(10):
            make_project(api, name=f'P{i}')
        assert post_json(api, '/api/projects/', {'name': 'jedenasta'}).status_code == 402
        services.activate_demo(org, 'business')
        assert post_json(api, '/api/projects/', {'name': 'jedenasta'}).status_code == 201

    def test_member_limit_not_reached(self, org):
        services.check_member_limit(org)  # w organizacji jest tylko administrator, limit planu Start to 2

    def test_member_limit_reached(self, org, inspector):
        with pytest.raises(HttpError) as exc:
            services.check_member_limit(org)
        assert exc.value.status_code == 402

    def test_member_limit_unlimited_plan(self, org, inspector):
        services.activate_demo(org, 'business')
        services.check_member_limit(org)

    def test_expired_subscription_falls_back_to_free(self, org):
        services.activate_demo(org, 'pro')
        Subscription.objects.update(status='canceled')
        assert services.effective_plan(org) == 'free'

    def test_past_due_keeps_access(self, org):
        services.activate_demo(org, 'pro')
        Subscription.objects.update(status='past_due')
        assert services.effective_plan(org) == 'pro'


class TestSubscriptionEndpoint:
    def test_usage_counts_projects(self, api, project):
        data = api.get('/api/billing/subscription').json()
        assert (data['plan'], data['projects_used']) == ('pro', 1)  # fixture project włącza Pro

    def test_summary_without_subscription_record(self, api):
        data = api.get('/api/billing/subscription').json()
        assert (data['plan'], data['plan_name'], data['projects_limit'], data['has_customer']) == ('free', 'Start', 1, False)

    def test_summary_with_subscription(self, api, org):
        services.activate_demo(org, 'pro')
        data = api.get('/api/billing/subscription').json()
        assert data['is_demo'] and data['current_period_end'] and data['projects_limit'] == 10


class TestDemoCheckout:
    @pytest.fixture(autouse=True)
    def _demo_mode(self, settings):
        settings.DEBUG = True
        settings.STRIPE_SECRET_KEY = ''

    def test_demo_upgrade_and_downgrade(self, api):
        assert post_json(api, '/api/billing/checkout', {'plan': 'pro'}).json()['activated'] is True
        assert api.get('/api/billing/subscription').json()['plan'] == 'pro'
        assert post_json(api, '/api/billing/downgrade').json()['plan'] == 'free'

    def test_downgrade_only_for_demo_subscriptions(self, api):
        assert post_json(api, '/api/billing/downgrade').status_code == 400

    def test_unknown_plan(self, api):
        assert post_json(api, '/api/billing/checkout', {'plan': 'platynowy'}).status_code == 400
        assert post_json(api, '/api/billing/checkout', {'plan': 'free'}).status_code == 400

    def test_only_admin_can_buy(self, viewer_api):
        assert post_json(viewer_api, '/api/billing/checkout', {'plan': 'pro'}).status_code == 403
        assert post_json(viewer_api, '/api/billing/downgrade').status_code == 403
        assert post_json(viewer_api, '/api/billing/portal').status_code == 403


@override_settings(DEBUG=False, STRIPE_SECRET_KEY='')
def test_checkout_is_blocked_in_production_without_stripe(api):
    assert post_json(api, '/api/billing/checkout', {'plan': 'pro'}).status_code == 503


class TestStripeCheckout:
    def test_new_customer_checkout(self, api, org, stripe_on, fake_stripe):
        r = post_json(api, '/api/billing/checkout', {'plan': 'pro'})
        assert r.json()['url'] == 'https://checkout.stripe.test/s'
        sent = fake_stripe.calls['checkout']
        assert sent['line_items'][0]['price'] == 'price_pro' and sent['customer_email'] == 'jan.kowalski@firma.pl'
        assert sent['client_reference_id'] == str(org.pk) and sent['mode'] == 'subscription'
        assert fake_stripe.api_key == 'sk_test_x'

    def test_existing_customer_is_reused(self, api, org, stripe_on, fake_stripe):
        Subscription.objects.create(organization=org, stripe_customer_id='cus_1')
        post_json(api, '/api/billing/checkout', {'plan': 'business'})
        sent = fake_stripe.calls['checkout']
        assert sent['customer'] == 'cus_1' and 'customer_email' not in sent

    def test_portal_requires_customer(self, api, stripe_on):
        assert post_json(api, '/api/billing/portal').status_code == 400

    def test_portal_url(self, api, org, stripe_on, fake_stripe):
        Subscription.objects.create(organization=org, stripe_customer_id='cus_1')
        assert post_json(api, '/api/billing/portal').json()['url'] == 'https://billing.stripe.test/p'
        assert fake_stripe.calls['portal']['customer'] == 'cus_1'


class TestWebhook:
    URL = '/api/billing/webhook'

    def checkout_event(self, org, **obj):
        return {'id': 'evt_1', 'object': 'event', 'type': 'checkout.session.completed', 'data': {'object': {
            'mode': 'subscription', 'client_reference_id': str(org.pk), 'customer': 'cus_1', 'subscription': 'sub_1',
            'metadata': {'plan': 'pro'}, **obj}}}

    def send(self, client, payload, **kw):
        body, header = signed(payload, **kw)
        return client.post(self.URL, body, content_type='application/json', headers={'Stripe-Signature': header})

    def test_not_configured(self, client):
        assert client.post(self.URL, b'{}', content_type='application/json').status_code == 400

    def test_bad_signature(self, client, stripe_on):
        r = client.post(self.URL, b'{}', content_type='application/json', headers={'Stripe-Signature': 't=1,v1=zly'})
        assert r.status_code == 400 and 'podpis' in r.json()['detail']

    def test_invalid_payload(self, client, stripe_on):
        body = b'to nie json'
        t = int(time.time())
        digest = hmac.new(b'whsec_test', f'{t}.'.encode() + body, hashlib.sha256).hexdigest()
        r = client.post(self.URL, body, content_type='application/json', headers={'Stripe-Signature': f't={t},v1={digest}'})
        assert r.status_code == 400

    def test_signature_of_other_secret_is_rejected(self, client, org, stripe_on):
        assert self.send(client, self.checkout_event(org), secret='whsec_inny').status_code == 400

    def test_checkout_completed_activates_plan(self, client, org, stripe_on):
        Subscription.objects.create(organization=org)
        assert self.send(client, self.checkout_event(org)).json() == {'ok': True}
        sub = Subscription.objects.get(organization=org)
        assert (sub.plan, sub.status, sub.stripe_customer_id, sub.stripe_subscription_id, sub.is_demo) == ('pro', 'active', 'cus_1', 'sub_1', False)

    def test_checkout_for_unknown_organization_is_ignored(self, client, org, stripe_on):
        event = self.checkout_event(org)
        event['data']['object']['client_reference_id'] = '00000000-0000-0000-0000-000000000000'
        assert self.send(client, event).status_code == 200

    def test_checkout_without_plan_metadata_keeps_existing_plan(self, client, org, stripe_on):
        Subscription.objects.create(organization=org, plan='business')
        event = self.checkout_event(org)
        event['data']['object'].pop('metadata')
        event['data']['object']['customer'] = None
        self.send(client, event)
        assert Subscription.objects.get().plan == 'business'

    def test_organization_taken_from_metadata(self, client, org, stripe_on):
        Subscription.objects.create(organization=org)
        event = self.checkout_event(org, client_reference_id=None, metadata={'org': str(org.pk), 'plan': 'business'})
        self.send(client, event)
        assert Subscription.objects.get().plan == 'business'

    def test_non_subscription_checkout_is_ignored(self, client, org, stripe_on):
        Subscription.objects.create(organization=org)
        self.send(client, self.checkout_event(org, mode='payment'))
        assert Subscription.objects.get().plan == 'free'

    def subscription_event(self, kind, **obj):
        item = {'price': {'id': 'price_biz'}, 'current_period_end': 1893456000}
        return {'id': 'evt_2', 'object': 'event', 'type': kind, 'data': {'object': {
            'id': 'sub_1', 'customer': 'cus_1', 'status': 'active', 'cancel_at_period_end': True,
            'items': {'data': [item]}, **obj}}}

    def test_subscription_lifecycle(self, client, org, stripe_on):
        Subscription.objects.create(organization=org, stripe_subscription_id='sub_1')
        self.send(client, self.subscription_event('customer.subscription.updated'))
        sub = Subscription.objects.get()
        assert sub.plan == 'business' and sub.cancel_at_period_end and sub.current_period_end.year == 2030
        assert sub.is_demo is False

        self.send(client, self.subscription_event('customer.subscription.deleted', status='canceled'))
        sub.refresh_from_db()
        assert sub.status == 'canceled' and sub.effective_plan == 'free'

    def test_subscription_is_found_by_customer_id(self, client, org, stripe_on):
        Subscription.objects.create(organization=org, stripe_customer_id='cus_1')
        self.send(client, self.subscription_event('customer.subscription.created'))
        assert Subscription.objects.get().stripe_subscription_id == 'sub_1'

    def test_subscription_without_period_or_items(self, client, org, stripe_on):
        Subscription.objects.create(organization=org, stripe_subscription_id='sub_1', current_period_end=dt.datetime.now(dt.UTC))
        event = self.subscription_event('customer.subscription.updated', items={'data': []}, cancel_at_period_end=False)
        self.send(client, event)
        sub = Subscription.objects.get()
        assert sub.current_period_end is None and not sub.cancel_at_period_end and sub.plan == 'free'

    def test_period_end_on_subscription_object(self, org):
        sub = Subscription.objects.create(organization=org)
        services._sync(sub, {'id': 'sub_9', 'items': None, 'current_period_end': 1893456000, 'customer': None})
        assert sub.current_period_end.year == 2030

    def test_unknown_subscription_is_ignored(self, client, stripe_on):
        assert self.send(client, self.subscription_event('customer.subscription.updated', customer=None)).status_code == 200

    def test_unrelated_events_are_acknowledged(self, client, stripe_on):
        assert self.send(client, {'id': 'e', 'object': 'event', 'type': 'invoice.paid', 'data': {'object': {}}}).status_code == 200

    def test_parse_webhook_uses_stripe_verification(self, stripe_on):
        body, header = signed({'id': 'e', 'object': 'event', 'type': 'x', 'data': {'object': {}}})
        assert services.parse_webhook(body, header)['type'] == 'x'
        with pytest.raises(HttpError):
            services.parse_webhook(body, 't=1,v1=bad')


def test_models_and_admin(org):
    sub = Subscription.objects.create(organization=org)
    assert str(sub) == 'firma.pl - free (active)'
    assert PLANS['pro']['price_pln'] == 79
