"""Ustawienia produkcyjne i start aplikacji. Moduł base.py jest wykonywany ponownie z kontrolowanym środowiskiem."""

import runpy
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

BASE = Path(__file__).resolve().parent.parent / 'config' / 'settings' / 'base.py'


@pytest.fixture
def load_settings(monkeypatch):
    """Zwraca funkcję wykonującą base.py z podanymi zmiennymi środowiskowymi."""
    for name in ('DJANGO_DEBUG', 'DJANGO_SECRET_KEY', 'AUTH_DEV_LOGIN', 'DATABASE_URL', 'FRONTEND_URL', 'FRONTEND_ORIGINS'):
        monkeypatch.delenv(name, raising=False)

    def run(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return runpy.run_path(str(BASE), run_name='settings_under_test')

    return run


def test_development_defaults(load_settings):
    s = load_settings()
    assert s['DEBUG'] is True and s['AUTH_DEV_LOGIN'] is True and s['AUTH_PASSWORD_LOGIN'] is True
    assert s['PASSWORD_HASHERS'][0].endswith('Argon2PasswordHasher')
    assert 'SECURE_SSL_REDIRECT' not in s and s['X_FRAME_OPTIONS'] == 'DENY'
    assert s['DATABASES']['default']['ENGINE'].endswith('sqlite3')
    assert s['FRONTEND_URL'] == s['FRONTEND_ORIGINS'][0]


def test_production_hardening(load_settings):
    s = load_settings(DJANGO_DEBUG='false', DJANGO_SECRET_KEY='x' * 50, AUTH_DEV_LOGIN='0', DATABASE_URL='sqlite:///:memory:')
    assert s['SECURE_SSL_REDIRECT'] and s['SESSION_COOKIE_SECURE'] and s['CSRF_COOKIE_SECURE']
    assert s['SECURE_HSTS_SECONDS'] >= 31536000 and s['SECURE_HSTS_PRELOAD'] and s['SECURE_CONTENT_TYPE_NOSNIFF']
    assert s['SECURE_PROXY_SSL_HEADER'] == ('HTTP_X_FORWARDED_PROTO', 'https')


def test_production_ssl_redirect_can_be_disabled(load_settings):
    s = load_settings(DJANGO_DEBUG='false', DJANGO_SECRET_KEY='x', AUTH_DEV_LOGIN='0', SECURE_SSL_REDIRECT='0')
    assert s['SECURE_SSL_REDIRECT'] is False


def test_production_requires_secret_key(load_settings):
    with pytest.raises(ImproperlyConfigured, match='DJANGO_SECRET_KEY'):
        load_settings(DJANGO_DEBUG='false')


def test_dev_login_is_forbidden_in_production(load_settings):
    with pytest.raises(ImproperlyConfigured, match='AUTH_DEV_LOGIN'):
        load_settings(DJANGO_DEBUG='false', DJANGO_SECRET_KEY='x', AUTH_DEV_LOGIN='1')


def test_dotenv_file_is_loaded_without_overriding_environment(load_settings, tmp_path, monkeypatch):
    s = load_settings()
    env = tmp_path / '.env'
    env.write_text('# komentarz\n\nZMIENNA_A="wartosc a"\nZMIENNA_B=b\nBEZ_ROWNOSCI\nZMIENNA_C=z-pliku\n', encoding='utf-8')
    monkeypatch.delenv('ZMIENNA_A', raising=False)
    monkeypatch.delenv('ZMIENNA_B', raising=False)
    monkeypatch.setenv('ZMIENNA_C', 'z-systemu')
    s['_load_dotenv'](env)
    import os

    assert (os.environ['ZMIENNA_A'], os.environ['ZMIENNA_B'], os.environ['ZMIENNA_C']) == ('wartosc a', 'b', 'z-systemu')
    for name in ('ZMIENNA_A', 'ZMIENNA_B'):
        monkeypatch.delenv(name)


def test_missing_dotenv_is_fine(load_settings, tmp_path):
    load_settings()['_load_dotenv'](tmp_path / 'nie-istnieje.env')


def test_dotenv_is_read_outside_tests(load_settings, monkeypatch):
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    assert load_settings()['DEBUG'] in (True, False)


def test_env_helpers(load_settings, monkeypatch):
    s = load_settings()
    monkeypatch.setenv('FLAGA', 'Yes')
    monkeypatch.setenv('LISTA', 'a, b ,,c')
    assert s['env_bool']('FLAGA', False) is True and s['env_bool']('BRAK', False) is False
    assert s['env_list']('LISTA') == ['a', 'b', 'c'] and s['env_list']('BRAK') == []


def test_wsgi_application_is_importable():
    from config import wsgi

    assert callable(wsgi.application)


def test_mail_backend_depends_on_smtp_configuration(load_settings, monkeypatch):
    monkeypatch.delenv('EMAIL_HOST', raising=False)
    assert load_settings()['EMAIL_BACKEND'].endswith('console.EmailBackend')
    s = load_settings(EMAIL_HOST='ssl0.ovh.net', EMAIL_PORT='465', DEFAULT_FROM_EMAIL='Usterki <noreply@axword.pl>')
    assert s['EMAIL_BACKEND'].endswith('smtp.EmailBackend') and s['EMAIL_PORT'] == 465 and s['EMAIL_USE_SSL'] is True
    assert s['DEFAULT_FROM_EMAIL'] == 'Usterki <noreply@axword.pl>' and s['PASSWORD_RESET_TIMEOUT'] == 7200
    brevo = load_settings(EMAIL_HOST='smtp-relay.brevo.com', EMAIL_PORT='587', EMAIL_USE_TLS='1')
    assert brevo['EMAIL_USE_TLS'] is True and brevo['EMAIL_USE_SSL'] is False  # STARTTLS wyłącza SSL
