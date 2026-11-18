from django.conf import settings
from django.core import signing
from ninja.errors import HttpError
from ninja.security import HttpBearer

from . import entra

DEV_PREFIX = 'dev.'
DEV_SALT = 'usterka.dev-login'
PWD_PREFIX = 'pwd.'  # noqa: S105
PWD_SALT = 'usterka.password-login'  # noqa: S105


def make_dev_token(user_id: int) -> str:
    return DEV_PREFIX + signing.dumps({'uid': user_id}, salt=DEV_SALT)


def make_password_token(user_id: int) -> str:
    return PWD_PREFIX + signing.dumps({'uid': user_id}, salt=PWD_SALT)


class ApiAuth(HttpBearer):
    """Bearer: token Microsoft (access token dla naszego API) albo token logowania deweloperskiego."""

    def authenticate(self, request, token):
        from users.models import User
        from users.services import user_from_entra_claims

        if token.startswith(DEV_PREFIX):
            if not settings.AUTH_DEV_LOGIN:
                raise HttpError(401, 'Logowanie deweloperskie jest wyłączone.')
            try:
                data = signing.loads(token[len(DEV_PREFIX):], salt=DEV_SALT, max_age=settings.DEV_TOKEN_MAX_AGE)
            except signing.BadSignature as exc:
                raise HttpError(401, 'Sesja wygasła. Zaloguj się ponownie.') from exc
            user = User.objects.filter(pk=data['uid'], is_active=True).first()
            request.ms_token = None
        elif token.startswith(PWD_PREFIX):
            if not settings.AUTH_PASSWORD_LOGIN:
                raise HttpError(401, 'Logowanie hasłem jest wyłączone.')
            try:
                data = signing.loads(token[len(PWD_PREFIX):], salt=PWD_SALT, max_age=settings.PASSWORD_TOKEN_MAX_AGE)
            except signing.BadSignature as exc:
                raise HttpError(401, 'Sesja wygasła. Zaloguj się ponownie.') from exc
            user = User.objects.filter(pk=data['uid'], is_active=True).first()
            request.ms_token = None
        else:
            try:
                claims = entra.validate_token(token)
            except entra.EntraTokenError as exc:
                raise HttpError(401, str(exc)) from exc
            user = user_from_entra_claims(claims)
            request.ms_token = token
        if not user:
            raise HttpError(401, 'Nieznany użytkownik.')
        request.user = user
        return user
