import datetime as dt

from ninja import File, Form, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile

from core.access import get_plan, get_project
from core.files import inspect_image, new_name, serve

from .models import Plan

router = Router()


class PlanOut(Schema):
    id: str
    project_id: str
    name: str
    width: int
    height: int
    source_filename: str
    source_page: int | None
    created_at: dt.datetime


class PlanPatch(Schema):
    name: str


def _out(p: Plan) -> dict:
    return {
        'id': str(p.id), 'project_id': str(p.project_id), 'name': p.name, 'width': p.width, 'height': p.height,
        'source_filename': p.source_filename, 'source_page': p.source_page, 'created_at': p.created_at,
    }


@router.get('/projects/{project_id}/plans', response=list[PlanOut])
def list_plans(request, project_id: str):
    return [_out(p) for p in get_project(request, project_id).plans.all()]


@router.post('/projects/{project_id}/plans', response={201: PlanOut})
def create_plan(
    request,
    project_id: str,
    name: str = Form(...),
    source_filename: str = Form(''),
    source_page: int | None = Form(None),
    image: UploadedFile = File(...),
):
    project = get_project(request, project_id, write=True)
    if not project.is_complete:
        raise HttpError(400, 'Uzupełnij wszystkie dane inwestycji, aby dodać plan.')
    w, h, ext = inspect_image(image, max_bytes=40 * 1024 * 1024)
    plan = Plan(project=project, name=name.strip() or 'Plan', width=w, height=h,
                source_filename=source_filename[:300], source_page=source_page)
    plan.image.save(new_name(ext), image, save=False)
    plan.save()
    project.save(update_fields=['updated_at'])
    return 201, _out(plan)


@router.patch('/plans/{plan_id}', response=PlanOut)
def rename_plan(request, plan_id: str, data: PlanPatch):
    plan = get_plan(request, plan_id, write=True)
    if not data.name.strip():
        raise HttpError(400, 'Podaj nazwę planu.')
    plan.name = data.name.strip()[:200]
    plan.save(update_fields=['name', 'updated_at'])
    return _out(plan)


@router.delete('/plans/{plan_id}', response={204: None})
def delete_plan(request, plan_id: str):
    get_plan(request, plan_id, write=True).delete()
    return 204, None


@router.get('/plans/{plan_id}/image')
def plan_image(request, plan_id: str):
    return serve(get_plan(request, plan_id).image)
