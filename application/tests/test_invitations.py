"""Zaproszenia do zespołu i usuwanie osób."""

import datetime as dt
import re

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from organizations.models import Invitation, Membership
from tests.helpers import PASSWORD, post_json
from users.models import User

pytestmark = pytest.mark.django_db

URL = '/api/organization/invitations'


def invite(client, email='nowa@firma.pl', role='inspector'):
    return post_json(client, URL, {'email': email, 'role': role})


def raw_token() -> str:
    return re.search(r'/invite/([\w-]+)', mail.outbox[-1].body).group(1)


def accept(client, token, password=PASSWORD, name='Nowa Osoba'):
    return post_json(client, f'/api/auth/invitations/{token}/accept', {'password': password, 'name': name})


@pytest.fixture
def pro_org(org):
    from billing.services import activate_demo

    activate_demo(org, 'business')
    return org


class TestCreate:
    def test_creates_invitation_and_sends_mail(self, api, pro_org):
        r = invite(api, 'Nowa@Firma.pl', 'viewer')
        body = r.json()
        assert r.status_code == 201 and body['email'] == 'nowa@firma.pl' and body['role'] == 'viewer' and body['email_sent'] is True
        message = mail.outbox[0]
        assert message.to == ['nowa@firma.pl'] and 'Jan Kowalski' in message.body and 'osoba z podglądem' in message.body
        assert '/invite/' in message.body

    def test_only_hash_of_token_is_stored(self, api, pro_org):
        invite(api)
        assert raw_token() not in Invitation.objects.get().token_hash and len(Invitation.objects.get().token_hash) == 64

    def test_list_shows_only_pending_of_own_organization(self, api, other_api, pro_org):
        invite(api)
        expired = Invitation.objects.get()
        Invitation.objects.create(organization=expired.organization, email='stare@firma.pl', token_hash='x' * 64,
                                  expires_at=timezone.now() - dt.timedelta(days=1))
        Invitation.objects.create(organization=expired.organization, email='przyjete@firma.pl', token_hash='y' * 64,
                                  expires_at=timezone.now() + dt.timedelta(days=1), accepted_at=timezone.now())
        assert [i['email'] for i in api.get(URL).json()] == ['nowa@firma.pl']
        assert other_api.get(URL).json() == []

    def test_reinviting_replaces_previous_invitation(self, api, pro_org):
        invite(api)
        first = raw_token()
        invite(api, role='viewer')
        assert Invitation.objects.count() == 1 and Invitation.objects.get().role == 'viewer'
        assert accept(Client(), first).status_code == 404  # stary link nie działa

    @pytest.mark.parametrize('email', ['bez-malpy', 'a@b', ''])
    def test_invalid_email(self, api, pro_org, email):
        assert invite(api, email).status_code == 400

    def test_unknown_role(self, api, pro_org):
        assert invite(api, role='szef').status_code == 400

    def test_person_with_account_cannot_be_invited(self, api, pro_org, inspector):
        assert invite(api, 'ANNA.NOWAK@firma.pl').status_code == 409

    def test_admin_only(self, viewer_api, pro_org):
        assert invite(viewer_api).status_code == 403
        assert viewer_api.get(URL).status_code == 403

    def test_unverified_admin_cannot_invite(self, client):
        token = post_json(client, '/api/auth/register', {'email': 'ola@firma.pl', 'password': PASSWORD}).json()['token']
        r = invite(Client(headers={'Authorization': f'Bearer {token}'}))
        assert r.status_code == 403 and 'Potwierdź' in r.json()['detail']

    def test_free_plan_counts_pending_invitations(self, api, org):
        assert invite(api, 'a@firma.pl').status_code == 201  # administrator + 1 zaproszenie = limit 2
        assert invite(api, 'b@firma.pl').status_code == 402
        assert invite(api, 'a@firma.pl').status_code == 201  # ponowne zaproszenie tej samej osoby mieści się w limicie

    def test_mail_failure_is_reported_but_invitation_kept(self, api, pro_org, settings):
        settings.EMAIL_BACKEND = 'tests.test_account_emails.BrokenBackend'
        r = invite(api)
        assert r.status_code == 201 and r.json()['email_sent'] is False and Invitation.objects.count() == 1

    def test_invitation_without_inviter(self, api, pro_org):
        from organizations.invitations import send_invitation

        invite(api)
        inv = Invitation.objects.get()
        inv.invited_by = None
        send_invitation(inv, 'tok')
        assert 'Administrator zaprasza' in mail.outbox[-1].body

    def test_inviter_without_display_name_is_shown_by_email(self, api, pro_org, user):
        from organizations.invitations import send_invitation

        User.objects.filter(pk=user.pk).update(display_name='')
        invite(api)
        send_invitation(Invitation.objects.select_related('invited_by').get(), 'tok')
        assert 'jan.kowalski@firma.pl zaprasza' in mail.outbox[-1].body


class TestRevoke:
    def test_revoke(self, api, pro_org):
        invite(api)
        inv = Invitation.objects.get()
        assert api.delete(f'{URL}/{inv.pk}').status_code == 204 and not Invitation.objects.exists()
        assert accept(Client(), raw_token()).status_code == 404

    def test_unknown_or_foreign_invitation(self, api, other_api, pro_org):
        invite(api)
        inv = Invitation.objects.get()
        assert other_api.delete(f'{URL}/{inv.pk}').status_code == 404
        assert api.delete(f'{URL}/00000000-0000-0000-0000-000000000000').status_code == 404

    def test_admin_only(self, api, viewer_api, pro_org):
        invite(api)
        assert viewer_api.delete(f'{URL}/{Invitation.objects.get().pk}').status_code == 403


class TestAccept:
    def test_info_endpoint(self, api, pro_org, client):
        invite(api, 'nowa@firma.pl', 'viewer')
        info = client.get(f'/api/auth/invitations/{raw_token()}').json()
        assert info == {'organization_name': 'firma.pl', 'email': 'nowa@firma.pl', 'role': 'viewer'}

    def test_accepting_creates_verified_member_and_logs_in(self, api, pro_org, client):
        invite(api, 'nowa@firma.pl', 'viewer')
        r = accept(client, raw_token())
        assert r.status_code == 201
        me = Client(headers={'Authorization': f"Bearer {r.json()['token']}"}).get('/api/auth/me').json()
        assert (me['role'], me['email_verified'], me['organization_name'], me['display_name']) == ('viewer', True, 'firma.pl', 'Nowa Osoba')
        assert Invitation.objects.get().accepted_at is not None

    def test_name_defaults_to_email_prefix(self, api, pro_org, client):
        invite(api)
        accept(client, raw_token(), name=' ')
        assert User.objects.get(email='nowa@firma.pl').display_name == 'nowa'

    def test_invitation_is_single_use(self, api, pro_org, client):
        invite(api)
        token = raw_token()
        assert accept(client, token).status_code == 201
        assert accept(client, token).status_code == 404
        assert client.get(f'/api/auth/invitations/{token}').status_code == 404

    def test_expired_invitation(self, api, pro_org, client):
        invite(api)
        Invitation.objects.update(expires_at=timezone.now() - dt.timedelta(seconds=1))
        assert client.get(f'/api/auth/invitations/{raw_token()}').status_code == 404
        assert accept(client, raw_token()).status_code == 404

    def test_unknown_token(self, client):
        assert accept(client, 'nieistniejacy').status_code == 404

    @pytest.mark.parametrize('password', ['123', 'a' * 129, 'nowa@firma.pl'])
    def test_weak_password_keeps_invitation_valid(self, api, pro_org, client, password):
        invite(api)
        token = raw_token()
        assert accept(client, token, password).status_code == 400
        assert accept(client, token).status_code == 201

    def test_account_created_meanwhile_blocks_acceptance(self, api, pro_org, client):
        invite(api)
        User.objects.create_user(username='nowa@firma.pl', email='nowa@firma.pl')
        assert accept(client, raw_token()).status_code == 409

    def test_plan_downgrade_between_invite_and_accept(self, api, pro_org, client, inspector):
        from billing.models import Subscription

        invite(api)  # w planie Business, 2 osoby w zespole
        Subscription.objects.update(status='canceled')  # plan Start: limit 2 osoby, już zajęte
        assert accept(client, raw_token()).status_code == 402

    def test_disabled_password_login(self, api, pro_org, client, settings):
        invite(api)
        settings.AUTH_PASSWORD_LOGIN = False
        assert accept(client, raw_token()).status_code == 404

    def test_acceptance_is_rate_limited(self, client):
        codes = [accept(client, 'x').status_code for _ in range(11)]
        assert codes[-1] == 429

    def test_invited_person_works_in_the_inviting_organization(self, api, pro_org, client):
        invite(api)
        token = accept(client, raw_token()).json()['token']
        newcomer = Client(headers={'Authorization': f'Bearer {token}'})
        assert [m['email'] for m in newcomer.get('/api/organization/members').json()] == ['jan.kowalski@firma.pl', 'nowa@firma.pl']


class TestRemoveMember:
    def test_removes_membership_and_account(self, api, inspector):
        member = Membership.objects.get(user=inspector)
        assert api.delete(f'/api/organization/members/{member.pk}').status_code == 204
        assert not User.objects.filter(pk=inspector.pk).exists()

    def test_keeps_account_with_other_memberships(self, api, inspector, other_api):
        other_org = Membership.objects.get(user__email='obcy@inna.pl').organization
        Membership.objects.create(user=inspector, organization=other_org)
        member = Membership.objects.get(user=inspector, organization__name='firma.pl')
        api.delete(f'/api/organization/members/{member.pk}')
        assert User.objects.filter(pk=inspector.pk).exists()

    def test_cannot_remove_self(self, api, user):
        member = Membership.objects.get(user=user)
        assert api.delete(f'/api/organization/members/{member.pk}').status_code == 400

    def test_cannot_remove_from_other_organization(self, api, other_api):
        foreign = Membership.objects.get(user__email='obcy@inna.pl')
        assert api.delete(f'/api/organization/members/{foreign.pk}').status_code == 404

    def test_admin_only(self, viewer_api, inspector):
        member = Membership.objects.get(user=inspector)
        assert viewer_api.delete(f'/api/organization/members/{member.pk}').status_code == 403

    def test_freed_email_can_be_invited_again(self, api, pro_org, inspector):
        api.delete(f'/api/organization/members/{Membership.objects.get(user=inspector).pk}')
        assert invite(api, 'anna.nowak@firma.pl').status_code == 201


def test_invitation_str_and_state(org, user):
    inv = Invitation.objects.create(organization=org, email='a@b.pl', token_hash='z' * 64, invited_by=user,
                                    expires_at=timezone.now() + dt.timedelta(days=1))
    assert str(inv) == 'Zaproszenie a@b.pl do firma.pl' and inv.is_pending
    inv.accepted_at = timezone.now()
    assert not inv.is_pending
