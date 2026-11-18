"""Zaproszenia do organizacji: tworzenie, wysyłka, przyjęcie."""

import datetime as dt
import hashlib
import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from ninja.errors import HttpError

from billing.services import check_member_limit
from core.mail import frontend_link, send_text
from users.models import User

from .models import Invitation, Membership

ROLES = {'admin', 'inspector', 'viewer'}
ROLE_NAMES = {'admin': 'administrator', 'inspector': 'inspektor', 'viewer': 'osoba z podglądem'}


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def pending(org):
    return Invitation.objects.filter(organization=org, accepted_at__isnull=True, expires_at__gt=timezone.now())


def create_invitation(org, inviter: User, email: str, role: str) -> tuple[Invitation, str]:
    email = email.strip().lower()
    if role not in ROLES:
        raise HttpError(400, 'Nieznana rola.')
    if User.objects.filter(email__iexact=email).exists():
        raise HttpError(409, 'Ta osoba ma już konto w aplikacji. Zaproszenia są dla adresów bez konta.')
    with transaction.atomic():
        pending(org).filter(email__iexact=email).delete()  # ponowne zaproszenie zastępuje poprzednie
        check_member_limit(org, pending_invitations=pending(org).count())
        raw = secrets.token_urlsafe(32)
        invitation = Invitation.objects.create(
            organization=org, email=email, role=role, token_hash=hash_token(raw), invited_by=inviter,
            expires_at=timezone.now() + dt.timedelta(days=settings.INVITATION_DAYS),
        )
    return invitation, raw


def send_invitation(invitation: Invitation, raw_token: str) -> bool:
    inviter = invitation.invited_by.display_name or invitation.invited_by.email if invitation.invited_by else 'Administrator'
    link = frontend_link(f'/invite/{raw_token}')
    return send_text(invitation.email, f'Zaproszenie do „{invitation.organization.name}”', (
        f'{inviter} zaprasza Cię do zespołu „{invitation.organization.name}” w aplikacji Usterki na planie '
        f'(rola: {ROLE_NAMES[invitation.role]}).\n\n'
        f'Załóż konto i dołącz: {link}\n\n'
        f'Zaproszenie jest ważne {settings.INVITATION_DAYS} dni.\n'
    ))


def get_pending_invitation(raw_token: str) -> Invitation:
    invitation = Invitation.objects.select_related('organization').filter(token_hash=hash_token(raw_token)).first()
    if invitation is None or not invitation.is_pending:
        raise HttpError(404, 'Zaproszenie jest nieprawidłowe, wygasło albo zostało już wykorzystane.')
    return invitation


@transaction.atomic
def accept_invitation(raw_token: str, password: str, name: str) -> User:
    invitation = get_pending_invitation(raw_token)
    if User.objects.filter(email__iexact=invitation.email).exists():
        raise HttpError(409, 'Konto z tym adresem e-mail już istnieje. Zaloguj się.')
    display = name.strip() or invitation.email.split('@')[0]
    candidate = User(username=invitation.email, email=invitation.email, first_name=display.split(' ')[0])
    try:
        validate_password(password, user=candidate)
    except ValidationError as exc:
        raise HttpError(400, ' '.join(exc.messages)) from exc
    if len(password) > 128:
        raise HttpError(400, 'Hasło może mieć maksymalnie 128 znaków.')
    # pending - 1: to zaproszenie samo zajmuje jedno miejsce, więc liczymy tylko pozostałe
    check_member_limit(invitation.organization, pending_invitations=pending(invitation.organization).count() - 1)
    user = User.objects.create_user(username=invitation.email, email=invitation.email, password=password,
                                    display_name=display, email_verified=True)  # link dotarł na ten adres
    Membership.objects.create(user=user, organization=invitation.organization, role=invitation.role)
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=['accepted_at', 'updated_at'])
    return user
