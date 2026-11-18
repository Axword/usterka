"""Ochrona logowania przed zgadywaniem haseł: blokada po serii nieudanych prób.

Liczniki trzymamy w cache Django. Lokalnie to pamięć procesu; przy kilku procesach/serwerach ustaw
wspólny cache (np. Redis) w CACHES, inaczej limit liczy się osobno na każdym procesie.
"""

from django.core.cache import cache
from ninja.errors import HttpError

MAX_FAILS = 5  # nieudanych prób na adres e-mail
MAX_FAILS_IP = 20  # nieudanych prób z jednego adresu IP
WINDOW = 15 * 60  # sekundy: okno liczenia i czas blokady
SIGNUP_PER_IP = 10  # rejestracji z jednego IP w oknie godzinnym


def client_ip(request) -> str:
    # Za reverse proxy ustaw SECURE_PROXY_SSL_HEADER i przekazuj X-Forwarded-For tylko z zaufanego proxy.
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')) or 'unknown'


def _keys(request, email: str):
    return f'login-fail:email:{email.lower()}', f'login-fail:ip:{client_ip(request)}'


def check_login_allowed(request, email: str):
    k_email, k_ip = _keys(request, email)
    if cache.get(k_email, 0) >= MAX_FAILS or cache.get(k_ip, 0) >= MAX_FAILS_IP:
        raise HttpError(429, 'Zbyt wiele nieudanych prób logowania. Spróbuj ponownie za 15 minut.')


def record_login_failure(request, email: str):
    for key in _keys(request, email):
        cache.add(key, 0, WINDOW)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, WINDOW)


def reset_login_failures(request, email: str):
    cache.delete(_keys(request, email)[0])


def check_signup_allowed(request):
    key = f'signup:ip:{client_ip(request)}'
    cache.add(key, 0, 3600)
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 3600)
        n = 1
    if n > SIGNUP_PER_IP:
        raise HttpError(429, 'Zbyt wiele rejestracji z tego adresu. Spróbuj później.')
