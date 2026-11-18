"""Kontrola dostępu: każdy zasób należy do organizacji, użytkownik widzi tylko swoją."""

from ninja.errors import HttpError

WRITE_ROLES = {'admin', 'inspector'}


def membership(request):
    cached = getattr(request, '_membership', None)
    if cached:
        return cached
    from organizations.models import Membership

    m = Membership.objects.select_related('organization').filter(user=request.auth).order_by('created_at').first()
    if not m:
        raise HttpError(403, 'Nie należysz do żadnej organizacji.')
    request._membership = m
    return m


def organization(request):
    return membership(request).organization


def require_write(request):
    if membership(request).role not in WRITE_ROLES:
        raise HttpError(403, 'Masz dostęp tylko do podglądu.')


def require_admin(request):
    if membership(request).role != 'admin':
        raise HttpError(403, 'Tylko administrator organizacji może to zmienić.')


def get_project(request, project_id, *, write=False):
    from projects.models import Project

    if write:
        require_write(request)
    p = Project.objects.filter(pk=project_id, organization=organization(request)).first()
    if not p:
        raise HttpError(404, 'Nie znaleziono inwestycji.')
    return p


def get_plan(request, plan_id, *, write=False):
    from plans.models import Plan

    if write:
        require_write(request)
    p = Plan.objects.select_related('project').filter(pk=plan_id, project__organization=organization(request)).first()
    if not p:
        raise HttpError(404, 'Nie znaleziono planu.')
    return p


def get_defect(request, defect_id, *, write=False):
    from defects.models import Defect

    if write:
        require_write(request)
    d = Defect.objects.select_related('project', 'plan').filter(pk=defect_id, project__organization=organization(request)).first()
    if not d:
        raise HttpError(404, 'Nie znaleziono usterki.')
    return d
