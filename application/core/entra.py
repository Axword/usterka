"""Walidacja tokenów Microsoft Entra ID (v1 i v2) wydanych dla naszego API."""

from functools import lru_cache

import jwt
from django.conf import settings

GENERIC_TENANTS = {'common', 'organizations', 'consumers'}


class EntraTokenError(Exception):
    pass


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient('https://login.microsoftonline.com/common/discovery/v2.0/keys', cache_keys=True, lifespan=3600)


def _allowed_audiences() -> list[str]:
    return [a for a in {settings.ENTRA_API_AUDIENCE, settings.ENTRA_CLIENT_ID} if a]


def validate_token(token: str) -> dict:
    if not settings.ENTRA_CLIENT_ID:
        raise EntraTokenError('Logowanie Microsoft nie jest skonfigurowane (ENTRA_CLIENT_ID).')
    try:
        key = _jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=_allowed_audiences(),
            options={'require': ['exp', 'iat', 'iss', 'aud']},
            leeway=60,
        )
    except jwt.PyJWTError as exc:
        raise EntraTokenError(f'Nieprawidłowy token: {exc}') from exc

    tid, oid = claims.get('tid'), claims.get('oid')
    if not tid or not oid:
        raise EntraTokenError('Token bez identyfikatora dzierżawy lub użytkownika.')
    if claims['iss'] not in (f'https://login.microsoftonline.com/{tid}/v2.0', f'https://sts.windows.net/{tid}/'):
        raise EntraTokenError('Nieprawidłowy wystawca tokenu.')
    if settings.ENTRA_TENANT not in GENERIC_TENANTS and tid != settings.ENTRA_TENANT:
        raise EntraTokenError('Ta dzierżawa Microsoft nie ma dostępu do aplikacji.')
    return claims
