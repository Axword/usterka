import datetime as dt
import re

from ninja import Router, Schema, Status
from ninja.errors import HttpError

from core.access import membership, organization, require_admin

from . import invitations
from .models import Invitation, Membership

router = Router()
SP_SITE_RE = re.compile(r'^https://[^\s/]+\.sharepoint\.com/sites/[^\s]+$', re.I)


class OrganizationOut(Schema):
    id: str
    name: str
    defect_types: list[str]
    sp_site_url: str
    sp_library: str
    sp_folder: str
    sharepoint_configured: bool


class OrganizationIn(Schema):
    name: str | None = None
    defect_types: list[str] | None = None
    sp_site_url: str | None = None
    sp_library: str | None = None
    sp_folder: str | None = None


class MemberOut(Schema):
    id: int
    email: str
    display_name: str
    role: str


class MemberIn(Schema):
    role: str


def _out(o):
    return {
        'id': str(o.id), 'name': o.name, 'defect_types': o.defect_types, 'sp_site_url': o.sp_site_url,
        'sp_library': o.sp_library, 'sp_folder': o.sp_folder,
        'sharepoint_configured': bool(o.sp_site_url and o.sp_library),
    }


@router.get('', response=OrganizationOut)
def get_org(request):
    return _out(organization(request))


@router.patch('', response=OrganizationOut)
def update_org(request, data: OrganizationIn):
    require_admin(request)
    o = organization(request)
    payload = data.dict(exclude_unset=True)
    if 'sp_site_url' in payload:
        url = (payload['sp_site_url'] or '').strip().rstrip('/')
        if url and not SP_SITE_RE.match(url):
            raise HttpError(400, 'Adres powinien wyglądać tak: https://firma.sharepoint.com/sites/nazwa')
        payload['sp_site_url'] = url
    if 'defect_types' in payload:
        types = [t.strip() for t in payload['defect_types'] if t and t.strip()]
        if not types:
            raise HttpError(400, 'Podaj co najmniej jeden rodzaj usterki.')
        payload['defect_types'] = list(dict.fromkeys(types))
    for k, v in payload.items():
        setattr(o, k, v.strip() if isinstance(v, str) else v)
    o.save()
    return _out(o)


@router.get('/members', response=list[MemberOut])
def members(request):
    o = organization(request)
    return [
        {'id': m.pk, 'email': m.user.email, 'display_name': m.user.display_name, 'role': m.role}
        for m in Membership.objects.filter(organization=o).select_related('user').order_by('user__email')
    ]


@router.patch('/members/{member_id}', response=MemberOut)
def set_role(request, member_id: int, data: MemberIn):
    require_admin(request)
    if data.role not in dict(Membership.ROLES):
        raise HttpError(400, 'Nieznana rola.')
    m = Membership.objects.select_related('user').filter(pk=member_id, organization=organization(request)).first()
    if not m:
        raise HttpError(404, 'Nie znaleziono osoby.')
    if m.pk == membership(request).pk and data.role != 'admin':
        raise HttpError(400, 'Nie możesz odebrać sobie roli administratora.')
    m.role = data.role
    m.save(update_fields=['role', 'updated_at'])
    return {'id': m.pk, 'email': m.user.email, 'display_name': m.user.display_name, 'role': m.role}


class InvitationIn(Schema):
    email: str
    role: str = 'inspector'


class InvitationOut(Schema):
    id: str
    email: str
    role: str
    created_at: dt.datetime
    expires_at: dt.datetime
    email_sent: bool = True


def _invitation_out(i: Invitation, email_sent: bool = True) -> dict:
    return {'id': str(i.id), 'email': i.email, 'role': i.role, 'created_at': i.created_at, 'expires_at': i.expires_at,
            'email_sent': email_sent}


@router.get('/invitations', response=list[InvitationOut])
def list_invitations(request):
    require_admin(request)
    return [_invitation_out(i) for i in invitations.pending(organization(request))]


@router.post('/invitations', response={201: InvitationOut})
def create_invitation(request, data: InvitationIn):
    require_admin(request)
    if not request.auth.email_verified:
        raise HttpError(403, 'Potwierdź swój adres e-mail, zanim zaprosisz kogoś do zespołu.')
    if '@' not in data.email or '.' not in data.email.rsplit('@', 1)[-1]:
        raise HttpError(400, 'Podaj poprawny adres e-mail.')
    invitation, raw = invitations.create_invitation(organization(request), request.auth, data.email, data.role)
    return Status(201, _invitation_out(invitation, email_sent=invitations.send_invitation(invitation, raw)))


@router.delete('/invitations/{invitation_id}', response={204: None})
def revoke_invitation(request, invitation_id: str):
    require_admin(request)
    deleted, _ = invitations.pending(organization(request)).filter(pk=invitation_id).delete()
    if not deleted:
        raise HttpError(404, 'Nie znaleziono zaproszenia.')
    return Status(204, None)


@router.delete('/members/{member_id}', response={204: None})
def remove_member(request, member_id: int):
    """Usuwa osobę z organizacji. Konto wiązane tylko z tą organizacją jest kasowane (zwalnia adres e-mail)."""
    require_admin(request)
    m = Membership.objects.select_related('user').filter(pk=member_id, organization=organization(request)).first()
    if not m:
        raise HttpError(404, 'Nie znaleziono osoby.')
    if m.pk == membership(request).pk:
        raise HttpError(400, 'Nie możesz usunąć samego siebie.')
    user = m.user
    m.delete()
    if not user.memberships.exists():
        user.delete()
    return Status(204, None)
