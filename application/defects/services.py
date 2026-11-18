import datetime as dt

from django.db import transaction
from django.utils import timezone
from ninja.errors import HttpError

from projects.models import Project

from .models import Defect, DefectEvent

EDITABLE = ['plan_id', 'x', 'y', 'type', 'type_other', 'description', 'due_mode', 'due_date', 'zoom', 'fixed_date']


def _validate(d: Defect, allowed_types: list[str]):
    errors = []
    if d.type not in allowed_types:
        errors.append('Wybierz rodzaj usterki.')
    if not d.description.strip():
        errors.append('Wpisz opis usterki.')
    if d.due_mode not in ('umowa', 'data') or (d.due_mode == 'data' and not d.due_date):
        errors.append('Wybierz termin usunięcia.')
    if not (0 <= d.x <= 1 and 0 <= d.y <= 1):
        errors.append('Znacznik poza planem.')
    if errors:
        raise HttpError(400, ' '.join(errors))
    if d.type != 'Inna':
        d.type_other = ''
    if d.due_mode == 'umowa':
        d.due_date = None
    d.description = d.description.strip()
    d.zoom = min(0.6, max(0.1, d.zoom))


def _serializable(v):
    return v.isoformat() if isinstance(v, dt.date) else str(v) if v is not None and not isinstance(v, (int, float, str)) else v


def log(defect, user, action, changes=None):
    DefectEvent.objects.create(defect=defect, user=user, action=action, changes=changes or {})


@transaction.atomic
def create_defect(project: Project, user, data: dict, allowed_types: list[str]) -> Defect:
    d = Defect(project=project, created_by=user, no=0, **{k: v for k, v in data.items() if v is not None})
    _validate(d, allowed_types)
    # Numer nadaje serwer pod blokadą wiersza inwestycji - dwie osoby nie dostaną tego samego numeru.
    locked = Project.objects.select_for_update().get(pk=project.pk)
    d.no = locked.next_no
    locked.next_no += 1
    locked.save(update_fields=['next_no', 'updated_at'])
    d.save()
    log(d, user, 'created', {'no': d.no})
    return d


@transaction.atomic
def update_defect(d: Defect, user, data: dict, allowed_types: list[str]) -> Defect:
    changes = {}
    for k, v in data.items():
        if k in EDITABLE and getattr(d, k) != v:
            changes[k] = [_serializable(getattr(d, k)), _serializable(v)]
            setattr(d, k, v)
    _validate(d, allowed_types)
    if d.status == 'fixed' and not d.fixed_date:
        d.fixed_date = timezone.localdate()
    if d.status == 'open':
        d.fixed_date = None
    d.save()
    d.project.save(update_fields=['updated_at'])
    if changes:
        log(d, user, 'updated', changes)
    return d


def refresh_status(d: Defect, user):
    """Jak w prototypie: zdjęcie „po” oznacza usterkę jako usuniętą."""
    has_after = d.photos.filter(kind='after').exists()
    new = 'fixed' if has_after else 'open'
    if new != d.status:
        d.status = new
        d.fixed_date = (d.fixed_date or timezone.localdate()) if new == 'fixed' else None
        d.save(update_fields=['status', 'fixed_date', 'updated_at'])
        log(d, user, 'status', {'status': new})
