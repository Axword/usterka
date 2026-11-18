"""Warstwa wspólna: weryfikacja tokenów Entra, dostęp, pliki, sygnały, błędy."""

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from ninja.errors import HttpError

from core import entra
from core.access import membership, organization, require_admin, require_write
from core.files import inspect_image, new_name, serve
from core.throttle import client_ip
from tests.helpers import image_file, make_project

pytestmark = pytest.mark.django_db

TENANT = '11111111-1111-1111-1111-111111111111'
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def signing_key(monkeypatch):
    """Podmienia pobieranie kluczy Microsoft na lokalny klucz testowy."""
    client = SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=KEY.public_key()))
    monkeypatch.setattr(entra, '_jwks_client', lambda: client)


def make_token(**overrides):
    now = int(time.time())
    claims = {'iss': f'https://login.microsoftonline.com/{TENANT}/v2.0', 'aud': 'api://test-client', 'exp': now + 600,
              'iat': now, 'tid': TENANT, 'oid': 'oid-1', **overrides}
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, KEY, algorithm='RS256')


class TestEntraTokenValidation:
    def test_valid_token(self, signing_key):
        claims = entra.validate_token(make_token())
        assert claims['oid'] == 'oid-1'

    def test_v1_issuer_is_accepted(self, signing_key):
        assert entra.validate_token(make_token(iss=f'https://sts.windows.net/{TENANT}/'))

    def test_not_configured(self):
        with override_settings(ENTRA_CLIENT_ID=''), pytest.raises(entra.EntraTokenError, match='nie jest skonfigurowane'):
            entra.validate_token('x')

    @pytest.mark.parametrize('overrides, message', [
        ({'aud': 'api://ktos-inny'}, 'Nieprawidłowy token'),
        ({'exp': 1}, 'Nieprawidłowy token'),
        ({'tid': None}, 'identyfikatora'),
        ({'oid': None}, 'identyfikatora'),
        ({'iss': 'https://zly.example/'}, 'wystawca'),
    ])
    def test_rejected_tokens(self, signing_key, overrides, message):
        with pytest.raises(entra.EntraTokenError, match=message):
            entra.validate_token(make_token(**overrides))

    def test_garbage_token(self, signing_key):
        with pytest.raises(entra.EntraTokenError):
            entra.validate_token('to-nie-jwt')

    def test_single_tenant_restriction(self, signing_key):
        with override_settings(ENTRA_TENANT='22222222-2222-2222-2222-222222222222'), \
                pytest.raises(entra.EntraTokenError, match='dzierżawa'):
            entra.validate_token(make_token())

    def test_single_tenant_match(self, signing_key):
        with override_settings(ENTRA_TENANT=TENANT):
            assert entra.validate_token(make_token())

    def test_audiences_include_client_id_and_api_uri(self):
        assert set(entra._allowed_audiences()) == {'api://test-client', 'test-client'}

    def test_jwks_client_is_created_once(self, monkeypatch):
        entra._jwks_client.cache_clear()
        monkeypatch.setattr(entra.jwt, 'PyJWKClient', lambda *a, **kw: object())
        assert entra._jwks_client() is entra._jwks_client()
        entra._jwks_client.cache_clear()


class TestAccessControl:
    def test_membership_is_cached_per_request(self, rf, user):
        request = rf.get('/')
        request.auth = user
        first = membership(request)
        assert membership(request) is first and organization(request) == first.organization

    def test_user_without_organization_is_forbidden(self, rf, db):
        from users.models import User

        request = rf.get('/')
        request.auth = User.objects.create_user(username='x', email='x@x.pl')
        with pytest.raises(HttpError) as exc:
            membership(request)
        assert exc.value.status_code == 403

    def test_role_checks(self, rf, user, viewer_api):
        from organizations.models import Membership

        request = rf.get('/')
        request.auth = user
        require_write(request)
        require_admin(request)

        Membership.objects.filter(user=user).update(role='inspector')
        request = rf.get('/')
        request.auth = user
        require_write(request)
        with pytest.raises(HttpError):
            require_admin(request)

        Membership.objects.filter(user=user).update(role='viewer')
        request = rf.get('/')
        request.auth = user
        with pytest.raises(HttpError):
            require_write(request)


class TestFiles:
    def test_inspect_accepts_supported_formats(self):
        for fmt, ext in (('JPEG', 'jpg'), ('PNG', 'png'), ('WEBP', 'webp')):
            assert inspect_image(image_file(fmt)) == (400, 300, ext)

    def test_rejects_oversized_file(self):
        big = SimpleUploadedFile('x.jpg', b'0' * 2048)
        with pytest.raises(HttpError) as exc:
            inspect_image(big, max_bytes=1024)
        assert exc.value.status_code == 413

    def test_rejects_unsupported_format(self):
        with pytest.raises(HttpError, match='Dozwolone formaty'):
            inspect_image(image_file('GIF'))

    def test_rejects_garbage(self):
        with pytest.raises(HttpError, match='poprawnym obrazem'):
            inspect_image(SimpleUploadedFile('x.jpg', b'smiec'))

    def test_new_name_is_unique(self):
        assert new_name('png').endswith('.png') and new_name('png') != new_name('png')

    def test_serve_without_file(self):
        with pytest.raises(HttpError) as exc:
            serve(None)
        assert exc.value.status_code == 404

    def test_serve_sets_headers(self, api, project, plan):
        from plans.models import Plan

        response = serve(Plan.objects.get(pk=plan['id']).image, filename='plan.jpg', as_attachment=True)
        response.close()
        assert response['Content-Type'] == 'image/jpeg' and 'attachment' in response['Content-Disposition']
        assert response['Cache-Control'] == 'private, max-age=86400'

    def test_serve_unknown_extension_falls_back_to_octet_stream(self):
        class Field:
            name = 'plik.nieznane-rozszerzenie'

            def __bool__(self):
                return True

            def open(self, mode):
                import io

                return io.BytesIO(b'x')

        response = serve(Field())
        response.close()
        assert response['Content-Type'] == 'application/octet-stream'


class TestFileCleanupSignals:
    def test_files_are_removed_with_records(self, api, project, plan, settings):
        assert any(settings.MEDIA_ROOT.rglob('*.jpg'))
        api.delete(f"/api/plans/{plan['id']}")
        assert not any(settings.MEDIA_ROOT.rglob('*.jpg'))

    def test_other_apps_are_ignored(self, user):
        from django.db.models.signals import post_delete

        from core.signals import delete_files

        class Fake:
            class _meta:  # noqa: N801
                app_label = 'auth'
                fields = []

        delete_files(Fake, object())  # nic nie robi i nie zgłasza błędu
        assert post_delete.receivers

    def test_storage_failure_is_logged_not_raised(self, api, project, plan, monkeypatch, caplog):
        from django.core.files.storage import FileSystemStorage

        def fail(self, name):
            raise OSError('zablokowany')

        monkeypatch.setattr(FileSystemStorage, 'delete', fail)
        with caplog.at_level('WARNING'):
            assert api.delete(f"/api/plans/{plan['id']}").status_code == 204
        assert 'Nie udało się usunąć pliku' in caplog.text

    def test_record_without_file_is_fine(self, api, pro):
        from projects.models import Project

        p = make_project(api)
        Project.objects.get(pk=p['id']).delete()  # projekt bez logo: puste pole pliku


class TestErrorHandlers:
    def test_object_does_not_exist_handler(self, rf):
        from django.core.exceptions import ObjectDoesNotExist

        from config.api import api

        handler = api._exception_handlers[ObjectDoesNotExist]
        response = handler(rf.get('/'), ObjectDoesNotExist())
        assert response.status_code == 404 and b'Nie znaleziono' in response.content

    def test_validation_error_with_messages(self, api, project):
        from tests.helpers import patch_json

        r = patch_json(api, f"/api/projects/{project['id']}", {'name': ''})
        assert r.status_code == 400 and r.json()['detail']

    def test_validation_error_without_messages_attribute(self, rf):
        from django.core.exceptions import ValidationError

        from config.api import api

        class Odd(ValidationError):
            def __init__(self):
                super().__init__('zepsuty')

            @property
            def messages(self):
                raise AttributeError

        handler = api._exception_handlers[ValidationError]
        assert handler(rf.get('/'), Odd()).status_code == 400


class TestClientIp:
    def test_uses_remote_addr(self, rf):
        assert client_ip(rf.get('/', REMOTE_ADDR='198.51.100.7')) == '198.51.100.7'

    def test_prefers_first_forwarded_address(self, rf):
        request = rf.get('/', HTTP_X_FORWARDED_FOR='203.0.113.5, 10.0.0.1', REMOTE_ADDR='10.0.0.1')
        assert client_ip(request) == '203.0.113.5'

    def test_unknown_when_nothing_available(self, rf):
        request = rf.get('/')
        request.META.pop('REMOTE_ADDR', None)
        assert client_ip(request) == 'unknown'


class TestThrottleRaces:
    """Licznik mógł wygasnąć między add() a incr() - kod ma sobie z tym radzić."""

    def test_login_counter_recovers_when_key_expires(self, monkeypatch, rf):
        from core import throttle

        def expired(key):
            raise ValueError(key)

        monkeypatch.setattr(throttle.cache, 'incr', expired)
        throttle.record_login_failure(rf.get('/'), 'a@b.pl')
        assert throttle.cache.get('login-fail:email:a@b.pl') == 1

    def test_signup_counter_recovers_when_key_expires(self, monkeypatch, rf):
        from core import throttle

        def expired(key):
            raise ValueError(key)

        monkeypatch.setattr(throttle.cache, 'incr', expired)
        throttle.check_signup_allowed(rf.get('/'))  # nie rzuca wyjątku, licznik startuje od 1
