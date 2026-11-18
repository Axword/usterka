"""Ustawienia Django. Wszystko, co zależy od środowiska, przychodzi ze zmiennych środowiskowych (.env)."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent  # application/config
APPLICATION_DIR = BASE_DIR.parent  # application/
ROOT_DIR = APPLICATION_DIR.parent  # repo


def _load_dotenv(path: Path) -> None:
    """Wczytuje .env z katalogu głównego repo (bez nadpisywania zmiennych już ustawionych)."""
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


if not os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('.test'):
    _load_dotenv(ROOT_DIR / '.env')


def env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in ('true', '1', 'yes')


def env_list(name: str, default: str = '') -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(',') if x.strip()]


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or 'django-insecure-local-usterka-development-key'
DEBUG = env_bool('DJANGO_DEBUG', True)
if not DEBUG and not os.getenv('DJANGO_SECRET_KEY'):
    raise ImproperlyConfigured('Ustaw DJANGO_SECRET_KEY przed uruchomieniem produkcyjnym.')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'core',
    'users',
    'organizations',
    'projects',
    'plans',
    'defects',
    'reports',
    'sharepoint',
    'billing',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASE_URL = os.getenv('DATABASE_URL') or f'sqlite:///{(APPLICATION_DIR / "sqlite3.db").as_posix()}'
DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=60)}

AUTH_USER_MODEL = 'users.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'pl'
TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = APPLICATION_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(APPLICATION_DIR / 'media')))

# Pliki (plany, zdjęcia, raporty) są wydawane tylko przez API z kontrolą dostępu, nigdy przez /media/.
DATA_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

FRONTEND_ORIGINS = env_list('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
CSRF_TRUSTED_ORIGINS = FRONTEND_ORIGINS

# ---------- Logowanie ----------
# AUTH_DEV_LOGIN=1 -> logowanie samym e-mailem (tylko lokalnie, bez Microsoft).
AUTH_DEV_LOGIN = env_bool('AUTH_DEV_LOGIN', DEBUG)
if AUTH_DEV_LOGIN and not DEBUG:
    raise ImproperlyConfigured('AUTH_DEV_LOGIN nie może być włączone przy DJANGO_DEBUG=false.')
DEV_TOKEN_MAX_AGE = 60 * 60 * 24 * 7
# Logowanie e-mailem i hasłem (własne konta). Bezpieczne na produkcji - domyślnie włączone.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
AUTH_PASSWORD_LOGIN = env_bool('AUTH_PASSWORD_LOGIN', True)
PASSWORD_TOKEN_MAX_AGE = 60 * 60 * 24 * 14

# ---------- Subskrypcje (Stripe) ----------
# Bez STRIPE_SECRET_KEY i przy DEBUG=true płatność jest symulowana (tryb demo). Patrz docs/06-subskrypcje-stripe.md
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICE_PRO = os.getenv('STRIPE_PRICE_PRO', '')
STRIPE_PRICE_BUSINESS = os.getenv('STRIPE_PRICE_BUSINESS', '')
FRONTEND_URL = os.getenv('FRONTEND_URL') or FRONTEND_ORIGINS[0]

# Microsoft Entra ID (Azure AD). Rejestracja aplikacji opisana w docs/05-konfiguracja-microsoft.md
ENTRA_CLIENT_ID = os.getenv('ENTRA_CLIENT_ID', '')
ENTRA_CLIENT_SECRET = os.getenv('ENTRA_CLIENT_SECRET', '')
# Aplikacja wielodostępna: 'organizations'. Jedna firma: ID dzierżawy.
ENTRA_TENANT = os.getenv('ENTRA_TENANT') or 'organizations'
# Audience tokenu dla naszego API, zwykle api://<client-id>
ENTRA_API_AUDIENCE = os.getenv('ENTRA_API_AUDIENCE') or (f'api://{ENTRA_CLIENT_ID}' if ENTRA_CLIENT_ID else '')
# 1 -> pierwsza osoba z nieznanej dzierżawy zakłada organizację i zostaje adminem.
ENTRA_ALLOW_ORG_SIGNUP = env_bool('ENTRA_ALLOW_ORG_SIGNUP', True)

GRAPH_SCOPES = ['https://graph.microsoft.com/Sites.ReadWrite.All']

# ---------- Bezpieczeństwo produkcyjne ----------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
}
