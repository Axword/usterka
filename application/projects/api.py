from django.db.models import Count, Q
from ninja import File, Router, Status
from ninja.files import UploadedFile

from billing.services import check_project_limit
from core.access import get_project, organization, require_write
from core.files import inspect_image, new_name, serve

from .models import Project
from .schemas import ProjectIn, ProjectOut, ProjectPatch, ReportSettings

router = Router()


def _annotated(qs):
    return qs.annotate(
        plans_count=Count('plans', distinct=True),
        open_count=Count('defects', filter=Q(defects__status='open'), distinct=True),
        fixed_count=Count('defects', filter=Q(defects__status='fixed'), distinct=True),
    )


def _out(p: Project) -> dict:
    return {
        'id': str(p.id), 'name': p.name, 'address': p.address, 'investor': p.investor, 'contractor': p.contractor,
        'inspection_date': p.inspection_date, 'author': p.author, 'has_logo': bool(p.logo),
        'is_complete': p.is_complete, 'report_settings': p.report_settings or {},
        'plans_count': getattr(p, 'plans_count', 0), 'open_count': getattr(p, 'open_count', 0),
        'fixed_count': getattr(p, 'fixed_count', 0), 'created_at': p.created_at, 'updated_at': p.updated_at,
    }


def _fresh(p: Project) -> dict:
    return _out(_annotated(Project.objects.filter(pk=p.pk)).get())


@router.get('', response=list[ProjectOut])
def list_projects(request):
    return [_out(p) for p in _annotated(Project.objects.filter(organization=organization(request)))]


@router.post('', response={201: ProjectOut})
def create_project(request, data: ProjectIn):
    require_write(request)
    check_project_limit(organization(request))
    p = Project.objects.create(organization=organization(request), created_by=request.auth, **data.dict())
    return Status(201, _fresh(p))


@router.get('/{project_id}', response=ProjectOut)
def get_project_view(request, project_id: str):
    return _fresh(get_project(request, project_id))


@router.patch('/{project_id}', response=ProjectOut)
def update_project(request, project_id: str, data: ProjectPatch):
    p = get_project(request, project_id, write=True)
    for k, v in data.dict(exclude_unset=True).items():
        setattr(p, k, v.strip() if isinstance(v, str) else v)
    p.full_clean(exclude=['logo'])
    p.save()
    return _fresh(p)


@router.delete('/{project_id}', response={204: None})
def delete_project(request, project_id: str):
    p = get_project(request, project_id, write=True)
    p.delete()  # kaskadowo plany, usterki, zdjęcia, raporty (pliki usuwa core.signals)
    return Status(204, None)


@router.put('/{project_id}/report-settings', response=ProjectOut)
def save_report_settings(request, project_id: str, data: ReportSettings):
    p = get_project(request, project_id, write=True)
    p.report_settings = data.dict(mode='json')
    p.save(update_fields=['report_settings', 'updated_at'])
    return _fresh(p)


@router.post('/{project_id}/logo', response=ProjectOut)
def upload_logo(request, project_id: str, file: UploadedFile = File(...)):
    p = get_project(request, project_id, write=True)
    _, _, ext = inspect_image(file, max_bytes=5 * 1024 * 1024)
    if p.logo:
        p.logo.delete(save=False)
    p.logo.save(new_name(ext), file, save=True)
    return _fresh(p)


@router.delete('/{project_id}/logo', response=ProjectOut)
def delete_logo(request, project_id: str):
    p = get_project(request, project_id, write=True)
    if p.logo:
        p.logo.delete(save=True)
    return _fresh(p)


@router.get('/{project_id}/logo')
def get_logo(request, project_id: str):
    return serve(get_project(request, project_id).logo)
