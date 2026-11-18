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
MAIL_PER_EMAIL = 5  # wiadomości na jeden adres w ciągu godziny
MAIL_PER_IP = 20  # wiadomości na żądania z jednego IP w ciągu godziny


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


def _hit(key: str, window: int) -> int:
    """Zlicza zdarzenie w oknie czasowym i zwraca bieżącą liczbę."""
    cache.add(key, 0, window)
    try:
        return cache.incr(key)
    except ValueError:  # licznik wygasł między add() a incr()
        cache.set(key, 1, window)
        return 1


def check_signup_allowed(request):
    if _hit(f'signup:ip:{client_ip(request)}', 3600) > SIGNUP_PER_IP:
        raise HttpError(429, 'Zbyt wiele rejestracji z tego adresu. Spróbuj później.')


def check_mail_allowed(request, kind: str, email: str):
    """Limit wiadomości wysyłanych na żądanie anonima (reset hasła itp.): chroni przed zalewaniem skrzynek."""
    if (_hit(f'mail:{kind}:email:{email.lower()}', 3600) > MAIL_PER_EMAIL
            or _hit(f'mail:{kind}:ip:{client_ip(request)}', 3600) > MAIL_PER_IP):
        raise HttpError(429, 'Zbyt wiele próśb. Spróbuj ponownie za godzinę.')
