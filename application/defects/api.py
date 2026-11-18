import datetime as dt
import uuid

from django.db.models import Max
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from core.access import get_defect, get_plan, get_project, organization, require_write
from core.files import inspect_image, new_name, serve

from . import services
from .models import Defect, Photo

router = Router()


class PhotoOut(Schema):
    id: str
    kind: str
    width: int
    height: int


class DefectOut(Schema):
    id: str
    project_id: str
    plan_id: str
    no: int
    x: float
    y: float
    type: str
    type_other: str
    description: str
    due_mode: str
    due_date: dt.date | None
    status: str
    fixed_date: dt.date | None
    zoom: float
    photos: list[PhotoOut]
    created_at: dt.datetime
    updated_at: dt.datetime


class DefectIn(Schema):
    id: uuid.UUID | None = None
    plan_id: uuid.UUID
    x: float
    y: float
    type: str
    type_other: str = ''
    description: str
    due_mode: str
    due_date: dt.date | None = None
    zoom: float = 0.3


class DefectPatch(Schema):
    plan_id: uuid.UUID | None = None
    x: float | None = None
    y: float | None = None
    type: str | None = None
    type_other: str | None = None
    description: str | None = None
    due_mode: str | None = None
    due_date: dt.date | None = None
    zoom: float | None = None
    fixed_date: dt.date | None = None


class EventOut(Schema):
    action: str
    changes: dict
    user: str
    created_at: dt.datetime


def _out(d: Defect) -> dict:
    return {
        'id': str(d.id), 'project_id': str(d.project_id), 'plan_id': str(d.plan_id), 'no': d.no, 'x': d.x, 'y': d.y,
        'type': d.type, 'type_other': d.type_other, 'description': d.description, 'due_mode': d.due_mode,
        'due_date': d.due_date, 'status': d.status, 'fixed_date': d.fixed_date, 'zoom': d.zoom,
        'photos': [{'id': str(p.id), 'kind': p.kind, 'width': p.width, 'height': p.height} for p in d.photos.all()],
        'created_at': d.created_at, 'updated_at': d.updated_at,
    }


def _reload(d: Defect) -> dict:
    return _out(Defect.objects.prefetch_related('photos').get(pk=d.pk))


@router.get('/projects/{project_id}/defects', response=list[DefectOut])
def list_defects(request, project_id: str, plan_id: str | None = None, status: str | None = None):
    qs = get_project(request, project_id).defects.prefetch_related('photos')
    if plan_id:
        qs = qs.filter(plan_id=plan_id)
    if status in ('open', 'fixed'):
        qs = qs.filter(status=status)
    return [_out(d) for d in qs]


@router.post('/projects/{project_id}/defects', response={201: DefectOut})
def create_defect(request, project_id: str, data: DefectIn):
    project = get_project(request, project_id, write=True)
    plan = get_plan(request, data.plan_id)
    if plan.project_id != project.id:
        raise HttpError(400, 'Plan należy do innej inwestycji.')
    payload = data.dict()
    if payload.get('id') is None or Defect.objects.filter(pk=payload['id']).exists():
        payload.pop('id')
    d = services.create_defect(project, request.auth, payload, organization(request).defect_types)
    return Status(201, _reload(d))


@router.get('/defects/{defect_id}', response=DefectOut)
def get_defect_view(request, defect_id: str):
    return _reload(get_defect(request, defect_id))


@router.patch('/defects/{defect_id}', response=DefectOut)
def update_defect(request, defect_id: str, data: DefectPatch):
    d = get_defect(request, defect_id, write=True)
    payload = data.dict(exclude_unset=True)
    if payload.get('plan_id'):
        plan = get_plan(request, payload['plan_id'])
        if plan.project_id != d.project_id:
            raise HttpError(400, 'Plan należy do innej inwestycji.')
    services.update_defect(d, request.auth, payload, organization(request).defect_types)
    return _reload(d)


@router.delete('/defects/{defect_id}', response={204: None})
def delete_defect(request, defect_id: str):
    d = get_defect(request, defect_id, write=True)
    for p in d.photos.all():
        p.delete()  # pojedynczo, żeby sygnał usunął pliki
    d.delete()
    return Status(204, None)


@router.get('/defects/{defect_id}/events', response=list[EventOut])
def defect_events(request, defect_id: str):
    d = get_defect(request, defect_id)
    return [
        {'action': e.action, 'changes': e.changes, 'user': str(e.user) if e.user else '', 'created_at': e.created_at}
        for e in d.events.select_related('user')
    ]


@router.post('/defects/{defect_id}/photos', response={201: DefectOut})
def add_photo(request, defect_id: str, kind: str = Form(...), file: UploadedFile = File(...)):
    d = get_defect(request, defect_id, write=True)
    if kind not in ('before', 'after'):
        raise HttpError(400, 'Nieznany rodzaj zdjęcia.')
    w, h, ext = inspect_image(file, max_bytes=15 * 1024 * 1024)
    order = (d.photos.filter(kind=kind).aggregate(m=Max('order'))['m'] or 0) + 1
    photo = Photo(defect=d, kind=kind, width=w, height=h, order=order, created_by=request.auth)
    photo.image.save(new_name(ext), file, save=False)
    photo.save()
    services.log(d, request.auth, 'photo_added', {'kind': kind})
    services.refresh_status(d, request.auth)
    return Status(201, _reload(d))


def _get_photo(request, photo_id: str) -> Photo:
    p = Photo.objects.select_related('defect__project').filter(
        pk=photo_id, defect__project__organization=organization(request)
    ).first()
    if not p:
        raise HttpError(404, 'Nie znaleziono zdjęcia.')
    return p


@router.delete('/photos/{photo_id}', response=DefectOut)
def delete_photo(request, photo_id: str):
    require_write(request)
    p = _get_photo(request, photo_id)
    d = p.defect
    kind = p.kind
    p.delete()
    services.log(d, request.auth, 'photo_removed', {'kind': kind})
    services.refresh_status(d, request.auth)
    return _reload(d)


@router.get('/photos/{photo_id}/file')
def photo_file(request, photo_id: str):
    return serve(_get_photo(request, photo_id).image)


@router.get('/defect-types', response=list[str])
def defect_types(request):
    return organization(request).defect_types
