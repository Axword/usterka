"""Wysyłka wiadomości e-mail. Błąd poczty nie może wywrócić żądania użytkownika (np. rejestracji)."""

import logging

from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger(__name__)


def frontend_link(path: str, **params: str) -> str:
    from urllib.parse import urlencode

    query = f'?{urlencode(params)}' if params else ''
    return f'{settings.FRONTEND_URL.rstrip("/")}{path}{query}'


def send_text(to: str, subject: str, body: str) -> bool:
    """Zwraca True, gdy poczta przyjęła wiadomość. Przy błędzie loguje go i zwraca False."""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception:  # noqa: BLE001 - SMTP może zawieść na wiele sposobów, użytkownik nie powinien widzieć 500
        log.exception('Nie udało się wysłać e-maila do %s (temat: %s)', to, subject)
        return False
    return True
