import datetime as dt

import stripe
from django.conf import settings
from ninja.errors import HttpError

from organizations.models import Membership

from .models import Subscription
from .plans import PLANS, plan_for_price, price_id


def get_subscription(org) -> Subscription | None:
    return Subscription.objects.filter(organization=org).first()


def effective_plan(org) -> str:
    sub = get_subscription(org)
    return sub.effective_plan if sub else 'free'


def check_project_limit(org):
    from projects.models import Project

    plan = effective_plan(org)
    limit = PLANS[plan]['max_projects']
    if limit is not None and Project.objects.filter(organization=org).count() >= limit:
        raise HttpError(402, f'Plan „{PLANS[plan]["name"]}” pozwala na {limit} inwestycji. Przejdź na wyższy plan w Subskrypcji.')


def check_member_limit(org):
    limit = PLANS[effective_plan(org)]['max_members']
    if limit is not None and Membership.objects.filter(organization=org).count() >= limit:
        raise HttpError(402, 'Osiągnięto limit osób w tym planie.')


def summary(org) -> dict:
    from projects.models import Project

    sub = get_subscription(org)
    plan = sub.effective_plan if sub else 'free'
    return {
        'plan': plan, 'plan_name': PLANS[plan]['name'], 'status': sub.status if sub else 'active',
        'current_period_end': sub.current_period_end if sub else None,
        'cancel_at_period_end': sub.cancel_at_period_end if sub else False,
        'is_demo': sub.is_demo if sub else False,
        'has_customer': bool(sub and sub.stripe_customer_id),
        'projects_used': Project.objects.filter(organization=org).count(),
        'projects_limit': PLANS[plan]['max_projects'],
    }


def _stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_checkout(org, user, plan: str) -> str:
    sub, _ = Subscription.objects.get_or_create(organization=org)
    kwargs = {'customer': sub.stripe_customer_id} if sub.stripe_customer_id else {'customer_email': user.email}
    session = _stripe().checkout.Session.create(
        mode='subscription', line_items=[{'price': price_id(plan), 'quantity': 1}],
        client_reference_id=str(org.pk), metadata={'org': str(org.pk), 'plan': plan},
        success_url=f'{settings.FRONTEND_URL}/subscription?paid=1', cancel_url=f'{settings.FRONTEND_URL}/subscription',
        allow_promotion_codes=True, **kwargs,
    )
    return session.url


def create_portal(org) -> str:
    sub = get_subscription(org)
    if not sub or not sub.stripe_customer_id:
        raise HttpError(400, 'Brak aktywnej subskrypcji do zarządzania.')
    return _stripe().billing_portal.Session.create(
        customer=sub.stripe_customer_id, return_url=f'{settings.FRONTEND_URL}/subscription').url


def activate_demo(org, plan: str):
    sub, _ = Subscription.objects.get_or_create(organization=org)
    sub.plan, sub.status, sub.is_demo = plan, 'active', True
    sub.current_period_end = dt.datetime.now(dt.UTC) + dt.timedelta(days=30)
    sub.cancel_at_period_end = False
    sub.save()


def _sync(sub: Subscription, obj: dict):
    item = ((obj.get('items') or {}).get('data') or [{}])[0]
    pid = (item.get('price') or {}).get('id', '')
    sub.stripe_subscription_id = obj['id']
    sub.stripe_customer_id = obj.get('customer') or sub.stripe_customer_id
    sub.status = obj.get('status', sub.status)
    sub.plan = plan_for_price(pid) or sub.plan
    end = item.get('current_period_end') or obj.get('current_period_end')
    sub.current_period_end = dt.datetime.fromtimestamp(end, dt.UTC) if end else None
    sub.cancel_at_period_end = bool(obj.get('cancel_at_period_end'))
    sub.is_demo = False
    sub.save()


def handle_event(event: dict):
    """Webhook Stripe: źródłem prawdy o płatności jest Stripe, nie przeglądarka."""
    kind, obj = event['type'], event['data']['object']
    if kind == 'checkout.session.completed' and obj.get('mode') == 'subscription':
        org_id = obj.get('client_reference_id') or (obj.get('metadata') or {}).get('org')
        sub = Subscription.objects.filter(organization_id=org_id).first()
        if sub:
            sub.stripe_customer_id = obj.get('customer') or ''
            sub.stripe_subscription_id = obj.get('subscription') or ''
            sub.plan = (obj.get('metadata') or {}).get('plan') or sub.plan
            sub.status, sub.is_demo = 'active', False
            sub.save()
    elif kind in ('customer.subscription.created', 'customer.subscription.updated', 'customer.subscription.deleted'):
        sub = (Subscription.objects.filter(stripe_subscription_id=obj['id']).first()
               or Subscription.objects.filter(stripe_customer_id=obj.get('customer') or '-').first())
        if sub:
            _sync(sub, obj)
            if kind.endswith('deleted'):
                sub.status = 'canceled'
                sub.save(update_fields=['status', 'updated_at'])


def parse_webhook(payload: bytes, sig: str) -> dict:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HttpError(400, 'Webhook nie jest skonfigurowany.')
    try:
        return stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HttpError(400, 'Nieprawidłowy podpis webhooka.') from exc
