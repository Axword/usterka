from django.conf import settings
from ninja import Router, Schema, Status
from ninja.errors import HttpError
from pydantic import EmailStr

from core.access import membership
from core.auth import make_dev_token, make_password_token

from . import emails
from .services import (
    confirm_password_reset,
    dev_login,
    login_with_password,
    register_with_password,
    request_password_reset,
    resend_verification,
)

router = Router()


class AuthConfigOut(Schema):
    dev_login: bool
    password_login: bool
    microsoft: bool
    client_id: str
    tenant: str
    api_scope: str


class DevLoginIn(Schema):
    email: EmailStr
    name: str = ''


class RegisterIn(Schema):
    email: EmailStr
    password: str
    name: str = ''
    company: str = ''


class PasswordLoginIn(Schema):
    email: EmailStr
    password: str


class TokenOut(Schema):
    token: str


class OkOut(Schema):
    ok: bool = True


class EmailIn(Schema):
    email: EmailStr


class ResetConfirmIn(Schema):
    uid: str
    token: str
    password: str


class VerifyIn(Schema):
    token: str


class MeOut(Schema):
    id: int
    email: str
    display_name: str
    microsoft: bool
    organization_id: str
    organization_name: str
    role: str
    email_verified: bool


@router.get('/config', auth=None, response=AuthConfigOut)
def auth_config(request):
    """Publiczna konfiguracja logowania dla frontendu."""
    return {
        'dev_login': settings.AUTH_DEV_LOGIN,
        'password_login': settings.AUTH_PASSWORD_LOGIN,
        'microsoft': bool(settings.ENTRA_CLIENT_ID),
        'client_id': settings.ENTRA_CLIENT_ID,
        'tenant': settings.ENTRA_TENANT,
        'api_scope': f'{settings.ENTRA_API_AUDIENCE}/access_as_user' if settings.ENTRA_API_AUDIENCE else '',
    }


@router.post('/dev-login', auth=None, response=TokenOut)
def dev_login_view(request, data: DevLoginIn):
    if not settings.AUTH_DEV_LOGIN:
        raise HttpError(404, 'Niedostępne.')
    user = dev_login(data.email, data.name)
    return {'token': make_dev_token(user.pk)}


@router.post('/register', auth=None, response={201: TokenOut})
def register_view(request, data: RegisterIn):
    if not settings.AUTH_PASSWORD_LOGIN:
        raise HttpError(404, 'Niedostępne.')
    user = register_with_password(request, data.email, data.password, data.name, data.company)
    return Status(201, {'token': make_password_token(user.pk)})


@router.post('/login', auth=None, response=TokenOut)
def password_login_view(request, data: PasswordLoginIn):
    if not settings.AUTH_PASSWORD_LOGIN:
        raise HttpError(404, 'Niedostępne.')
    user = login_with_password(request, data.email, data.password)
    return {'token': make_password_token(user.pk)}


@router.get('/me', response=MeOut)
def me(request):
    m = membership(request)
    u = request.auth
    return {
        'id': u.pk,
        'email': u.email,
        'display_name': u.display_name,
        'microsoft': bool(u.entra_oid),
        'organization_id': str(m.organization_id),
        'organization_name': m.organization.name,
        'role': m.role,
        'email_verified': u.email_verified,
    }


@router.post('/password-reset', auth=None, response=OkOut)
def password_reset_view(request, data: EmailIn):
    if not settings.AUTH_PASSWORD_LOGIN:
        raise HttpError(404, 'Niedostępne.')
    request_password_reset(request, data.email)
    return {'ok': True}


@router.post('/password-reset/confirm', auth=None, response=TokenOut)
def password_reset_confirm_view(request, data: ResetConfirmIn):
    if not settings.AUTH_PASSWORD_LOGIN:
        raise HttpError(404, 'Niedostępne.')
    user = confirm_password_reset(request, data.uid, data.token, data.password)
    return {'token': make_password_token(user.pk)}


@router.post('/verify-email', auth=None, response=OkOut)
def verify_email_view(request, data: VerifyIn):
    emails.verify_email(data.token)
    return {'ok': True}


@router.post('/resend-verification', response=OkOut)
def resend_verification_view(request):
    resend_verification(request, request.auth)
    return {'ok': True}


class InvitationInfoOut(Schema):
    organization_name: str
    email: str
    role: str


class InvitationAcceptIn(Schema):
    password: str
    name: str = ''


@router.get('/invitations/{token}', auth=None, response=InvitationInfoOut)
def invitation_info(request, token: str):
    from organizations.invitations import get_pending_invitation

    inv = get_pending_invitation(token)
    return {'organization_name': inv.organization.name, 'email': inv.email, 'role': inv.role}


@router.post('/invitations/{token}/accept', auth=None, response={201: TokenOut})
def invitation_accept(request, token: str, data: InvitationAcceptIn):
    from core.throttle import check_signup_allowed
    from organizations.invitations import accept_invitation

    if not settings.AUTH_PASSWORD_LOGIN:
        raise HttpError(404, 'Niedostępne.')
    check_signup_allowed(request)
    user = accept_invitation(token, data.password, data.name)
    return Status(201, {'token': make_password_token(user.pk)})
