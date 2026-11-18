"""Cennik. Limity egzekwowane są po stronie serwera (projects.api)."""

from django.conf import settings

PLANS = {
    'free': {'name': 'Start', 'price_pln': 0, 'max_projects': 1, 'max_members': 2,
             'features': ['1 inwestycja', '2 osoby w zespole', 'Raport PDF i Word']},
    'pro': {'name': 'Pro', 'price_pln': 79, 'max_projects': 10, 'max_members': 10,
            'features': ['10 inwestycji', '10 osób w zespole', 'Kopia raportów do SharePoint',
                         'Historia zmian usterek']},
    'business': {'name': 'Business', 'price_pln': 199, 'max_projects': None, 'max_members': None,
                 'features': ['Bez limitu inwestycji', 'Bez limitu osób', 'Logowanie kontami Microsoft',
                              'Priorytetowe wsparcie']},
}


def price_id(plan: str) -> str:
    return {'pro': settings.STRIPE_PRICE_PRO, 'business': settings.STRIPE_PRICE_BUSINESS}.get(plan, '')


def plan_for_price(pid: str) -> str | None:
    for plan in ('pro', 'business'):
        if pid and price_id(plan) == pid:
            return plan
    return None


def stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PRICE_PRO and settings.STRIPE_PRICE_BUSINESS)


def demo_mode() -> bool:
    return settings.DEBUG and not settings.STRIPE_SECRET_KEY
