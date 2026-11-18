import datetime as dt

from ninja import Router, Schema
from ninja.errors import HttpError

from core.access import organization, require_admin

from . import services
from .plans import PLANS, demo_mode, stripe_configured

router = Router()


class PlanOut(Schema):
    id: str
    name: str
    price_pln: int
    max_projects: int | None
    max_members: int | None
    features: list[str]


class PlansOut(Schema):
    plans: list[PlanOut]
    payments_enabled: bool
    demo_mode: bool


class SubscriptionOut(Schema):
    plan: str
    plan_name: str
    status: str
    current_period_end: dt.datetime | None
    cancel_at_period_end: bool
    is_demo: bool
    has_customer: bool
    projects_used: int
    projects_limit: int | None


class CheckoutIn(Schema):
    plan: str


class UrlOut(Schema):
    url: str | None = None
    activated: bool = False


@router.get('/plans', auth=None, response=PlansOut)
def plans(request):
    return {'plans': [{'id': k, **v} for k, v in PLANS.items()],
            'payments_enabled': stripe_configured(), 'demo_mode': demo_mode()}


@router.get('/subscription', response=SubscriptionOut)
def subscription(request):
    return services.summary(organization(request))


@router.post('/checkout', response=UrlOut)
def checkout(request, data: CheckoutIn):
    require_admin(request)
    if not request.auth.email_verified:
        raise HttpError(403, 'Potwierdź adres e-mail, zanim kupisz plan. Link wysłaliśmy po rejestracji.')
    if data.plan not in ('pro', 'business'):
        raise HttpError(400, 'Nieznany plan.')
    org = organization(request)
    if stripe_configured():
        return {'url': services.create_checkout(org, request.auth, data.plan)}
    if demo_mode():
        services.activate_demo(org, data.plan)
        return {'activated': True}
    raise HttpError(503, 'Płatności nie są jeszcze skonfigurowane.')


@router.post('/portal', response=UrlOut)
def portal(request):
    require_admin(request)
    return {'url': services.create_portal(organization(request))}


@router.post('/downgrade', response=SubscriptionOut)
def downgrade(request):
    """Tylko tryb demo. Prawdziwą subskrypcję anuluje się w portalu Stripe."""
    require_admin(request)
    org = organization(request)
    sub = services.get_subscription(org)
    if not (sub and sub.is_demo):
        raise HttpError(400, 'Subskrypcję zarządzasz w portalu płatności.')
    sub.plan, sub.is_demo = 'free', False
    sub.save()
    return services.summary(org)


@router.post('/webhook', auth=None, response={200: dict})
def webhook(request):
    event = services.parse_webhook(request.body, request.headers.get('Stripe-Signature', ''))
    services.handle_event(event)
    return {'ok': True}
