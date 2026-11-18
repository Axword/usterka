from .base import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
AUTH_DEV_LOGIN = True
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
MEDIA_ROOT = BASE_DIR.parent / '.test-media'  # noqa: F405
ENTRA_CLIENT_ID = 'test-client'
ENTRA_API_AUDIENCE = 'api://test-client'
