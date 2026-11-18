from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from ninja.errors import HttpError

from core.throttle import (
    check_login_allowed,
    check_mail_allowed,
    check_signup_allowed,
    record_login_failure,
    reset_login_failures,
)
from organizations.models import Membership, Organization

from . import emails
from .models import User

MAX_PASSWORD_LEN = 128


def _email_from_claims(c: dict) -> str:
    return (c.get('preferred_username') or c.get('upn') or c.get('email') or f"{c['oid']}@entra.local").lower()


@transaction.atomic
def user_from_entra_claims(c: dict) -> User:
    oid, tid = c['oid'], c['tid']
    email = _email_from_claims(c)
    name = c.get('name', '')

    user = User.objects.filter(entra_oid=oid).first() or User.objects.filter(email=email, entra_oid__isnull=True).first()
    if user is None:
        user = User.objects.create(username=oid, email=email, display_name=name, entra_oid=oid, entra_tenant_id=tid,
                                   email_verified=True)
    elif user.entra_oid != oid or user.email != email or (name and user.display_name != name):
        user.entra_oid, user.entra_tenant_id, user.email = oid, tid, email
        user.display_name = name or user.display_name
        user.save(update_fields=['entra_oid', 'entra_tenant_id', 'email', 'display_name'])
    if not user.is_active:
        raise HttpError(403, 'Konto jest zablokowane.')

    if not Membership.objects.filter(user=user).exists():
        org = Organization.objects.filter(entra_tenant_id=tid).first()
        if org is None:
            if not settings.ENTRA_ALLOW_ORG_SIGNUP:
                raise HttpError(403, 'Twoja firma nie ma jeszcze dostępu do aplikacji.')
            org = Organization.objects.create(name=email.split('@')[-1], entra_tenant_id=tid, email_domain=email.split('@')[-1])
            role = 'admin'
        else:
            role = 'inspector'
        Membership.objects.create(user=user, organization=org, role=role)
    return user


@transaction.atomic
def dev_login(email: str, name: str = '') -> User:
    email = email.strip().lower()
    domain = email.split('@')[-1]
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create(username=email, email=email, display_name=name or email.split('@')[0], email_verified=True)
    if not Membership.objects.filter(user=user).exists():
        org, created = Organization.objects.get_or_create(email_domain=domain, entra_tenant_id=None, defaults={'name': domain})
        Membership.objects.create(user=user, organization=org, role='admin' if created else 'inspector')
    return user


@transaction.atomic
def register_with_password(request, email: str, password: str, name: str, company: str) -> User:
    """Nowe konto z hasłem = nowa organizacja. Nie dołączamy do istniejącej po domenie: e-mail nie jest zweryfikowany."""
    check_signup_allowed(request)
    email = email.strip().lower()
    if User.objects.filter(email=email).exists():
        raise HttpError(409, 'Konto z tym adresem e-mail już istnieje. Zaloguj się.')
    _check_new_password(password, User(username=email, email=email, first_name=name.strip().split(' ')[0]))
    display = name.strip() or email.split('@')[0]
    user = User.objects.create_user(username=email, email=email, password=password, display_name=display)
    org = Organization.objects.create(name=company.strip() or f'Firma {user.display_name}')
    Membership.objects.create(user=user, organization=org, role='admin')
    emails.send_verification(user)
    return user


def login_with_password(request, email: str, password: str) -> User:
    email = email.strip().lower()
    check_login_allowed(request, email)
    # authenticate() liczy skrót także dla nieistniejącego konta, więc czas odpowiedzi nie zdradza, czy konto istnieje.
    user = authenticate(username=email, password=password) if len(password) <= MAX_PASSWORD_LEN else None
    if user is None or not user.is_active:
        record_login_failure(request, email)
        raise HttpError(401, 'Nieprawidłowy e-mail lub hasło.')
    reset_login_failures(request, email)
    return user


def _check_new_password(password: str, user: User):
    if len(password) > MAX_PASSWORD_LEN:
        raise HttpError(400, f'Hasło może mieć maksymalnie {MAX_PASSWORD_LEN} znaków.')
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise HttpError(400, ' '.join(exc.messages)) from exc


def request_password_reset(request, email: str) -> None:
    """Zawsze kończy się tak samo, niezależnie od tego, czy konto istnieje (brak zdradzania kont)."""
    email = email.strip().lower()
    check_mail_allowed(request, 'reset', email)
    user = User.objects.filter(email__iexact=email).first()
    if user and emails.can_reset_password(user):
        emails.send_password_reset(user)


def confirm_password_reset(request, uid: str, token: str, password: str) -> User:
    user = emails.user_from_reset_link(uid, token)
    if user is None:
        raise HttpError(400, 'Link jest nieprawidłowy lub wygasł. Poproś o nowy.')
    _check_new_password(password, user)
    user.set_password(password)
    user.email_verified = True  # link dotarł na skrzynkę tego adresu
    user.save(update_fields=['password', 'email_verified'])
    reset_login_failures(request, user.email)
    return user


def resend_verification(request, user: User) -> None:
    if user.email_verified:
        raise HttpError(400, 'Adres e-mail jest już potwierdzony.')
    check_mail_allowed(request, 'verify', user.email)
    if not emails.send_verification(user):
        raise HttpError(503, 'Nie udało się wysłać wiadomości. Spróbuj ponownie za chwilę.')
