"""Wiadomości i tokeny dla kont: potwierdzenie adresu e-mail oraz reset hasła."""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from ninja.errors import HttpError

from core.mail import frontend_link, send_text

from .models import User

VERIFY_SALT = 'usterka.verify-email'


def verification_token(user: User) -> str:
    return signing.dumps({'uid': user.pk, 'email': user.email}, salt=VERIFY_SALT)


def send_verification(user: User) -> bool:
    link = frontend_link('/verify-email', token=verification_token(user))
    return send_text(user.email, 'Potwierdź adres e-mail', (
        f'Cześć {user.display_name or ""},\n\n'
        f'potwierdź swój adres e-mail w aplikacji Usterki na planie, klikając w link:\n{link}\n\n'
        'Link jest ważny 3 dni. Jeśli to nie Ty zakładałeś konto, zignoruj tę wiadomość.\n'
    ))


def verify_email(token: str) -> User:
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFY_MAX_AGE)
    except signing.BadSignature as exc:
        raise HttpError(400, 'Link jest nieprawidłowy lub wygasł. Poproś o nowy.') from exc
    user = User.objects.filter(pk=data['uid'], email=data['email'], is_active=True).first()
    if user is None:
        raise HttpError(400, 'Link jest nieprawidłowy lub wygasł. Poproś o nowy.')
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=['email_verified'])
    return user


def can_reset_password(user: User) -> bool:
    """Konta Microsoft i konta bez własnego hasła (tryb dev) nie mają czego resetować."""
    return user.is_active and not user.entra_oid and bool(user.password) and user.has_usable_password()


def send_password_reset(user: User) -> bool:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = frontend_link('/reset-password', uid=uid, token=default_token_generator.make_token(user))
    hours = settings.PASSWORD_RESET_TIMEOUT // 3600
    return send_text(user.email, 'Reset hasła', (
        f'Cześć {user.display_name or ""},\n\n'
        f'ktoś (mamy nadzieję, że Ty) poprosił o zmianę hasła w aplikacji Usterki na planie:\n{link}\n\n'
        f'Link jest ważny {hours} godz. i działa jednorazowo. Jeśli to nie Ty, zignoruj wiadomość: hasło pozostanie bez zmian.\n'
    ))


def user_from_reset_link(uid: str, token: str) -> User | None:
    try:
        user = User.objects.filter(pk=int(urlsafe_base64_decode(uid).decode())).first()
    except (ValueError, TypeError, OverflowError):
        return None
    if user is None or not can_reset_password(user) or not default_token_generator.check_token(user, token):
        return None
    return user
