import datetime as dt
import logging

from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from core.access import get_project, organization, require_write
from core.files import new_name, serve
from sharepoint.graph import SharePointError, safe_segment, target_folder, upload_report

from .models import Report

router = Router()
log = logging.getLogger(__name__)

MAGIC = {'pdf': b'%PDF', 'docx': b'PK\x03\x04'}
MAX_REPORT = 200 * 1024 * 1024


class ReportOut(Schema):
    id: str
    project_id: str
    kind: str
    filename: str
    size: int
    document_date: dt.date
    defect_filter: str
    defects_count: int
    created_by: str
    created_at: dt.datetime
    sharepoint_status: str
    sharepoint_url: str
    sharepoint_path: str
    sharepoint_error: str


def _out(r: Report) -> dict:
    return {
        'id': str(r.id), 'project_id': str(r.project_id), 'kind': r.kind, 'filename': r.filename, 'size': r.size,
        'document_date': r.document_date, 'defect_filter': r.defect_filter, 'defects_count': r.defects_count,
        'created_by': str(r.created_by) if r.created_by else '', 'created_at': r.created_at,
        'sharepoint_status': r.sharepoint_status, 'sharepoint_url': r.sharepoint_url,
        'sharepoint_path': r.sharepoint_path, 'sharepoint_error': r.sharepoint_error,
    }


def _send_to_sharepoint(request, r: Report):
    org = organization(request)
    if not (org.sp_site_url and org.sp_library):
        raise HttpError(400, 'Uzupełnij adres witryny i bibliotekę SharePoint w ustawieniach organizacji.')
    token = getattr(request, 'ms_token', None)
    if not token:
        r.sharepoint_status, r.sharepoint_error = 'error', 'Zapis do SharePoint wymaga logowania kontem Microsoft.'
    else:
        try:
            with r.file.open('rb') as fh:
                res = upload_report(
                    user_assertion=token, tenant_id=request.auth.entra_tenant_id, site_url=org.sp_site_url,
                    library=org.sp_library, folder=target_folder(org.sp_folder, r.project.name),
                    filename=r.filename, data=fh.read(),
                )
            r.sharepoint_status, r.sharepoint_url, r.sharepoint_path, r.sharepoint_error = 'ok', res['web_url'], res['path'], ''
        except SharePointError as exc:
            r.sharepoint_status, r.sharepoint_error = 'error', str(exc)
        except Exception:  # noqa: BLE001 - błąd sieci itp. nie może zgubić raportu
            log.exception('SharePoint upload failed')
            r.sharepoint_status, r.sharepoint_error = 'error', 'Nieoczekiwany błąd połączenia z SharePoint.'
    r.save(update_fields=['sharepoint_status', 'sharepoint_url', 'sharepoint_path', 'sharepoint_error', 'updated_at'])


@router.get('/projects/{project_id}/reports', response=list[ReportOut])
def list_reports(request, project_id: str):
    return [_out(r) for r in get_project(request, project_id).reports.select_related('created_by')]


@router.post('/projects/{project_id}/reports', response={201: ReportOut})
def create_report(
    request,
    project_id: str,
    kind: str = Form(...),
    document_date: dt.date = Form(...),
    defect_filter: str = Form('all'),
    defects_count: int = Form(0),
    send_to_sharepoint: bool = Form(False),
    file: UploadedFile = File(...),
):
    project = get_project(request, project_id, write=True)
    if kind not in MAGIC:
        raise HttpError(400, 'Nieznany format raportu.')
    if file.size > MAX_REPORT:
        raise HttpError(413, 'Raport jest za duży.')
    head = file.read(4)
    file.seek(0)
    if head != MAGIC[kind]:
        raise HttpError(400, 'Plik nie jest poprawnym raportem.')
    filename = f'Protokol_usterek_{safe_segment(project.name).replace(" ", "_")[:80]}_{document_date:%d-%m-%Y}.{kind}'
    r = Report(project=project, kind=kind, filename=filename, size=file.size, document_date=document_date,
               defect_filter=defect_filter, defects_count=defects_count, created_by=request.auth)
    r.file.save(new_name(kind), file, save=False)
    r.save()
    if send_to_sharepoint:
        _send_to_sharepoint(request, r)
    return Status(201, _out(r))


def _get(request, report_id: str) -> Report:
    r = Report.objects.select_related('project', 'created_by').filter(
        pk=report_id, project__organization=organization(request)).first()
    if not r:
        raise HttpError(404, 'Nie znaleziono raportu.')
    return r


@router.post('/reports/{report_id}/sharepoint', response=ReportOut)
def retry_sharepoint(request, report_id: str):
    require_write(request)
    r = _get(request, report_id)
    _send_to_sharepoint(request, r)
    return _out(r)


@router.get('/reports/{report_id}/file')
def report_file(request, report_id: str):
    r = _get(request, report_id)
    return serve(r.file, filename=r.filename, as_attachment=True)


@router.delete('/reports/{report_id}', response={204: None})
def delete_report(request, report_id: str):
    require_write(request)
    _get(request, report_id).delete()
    return Status(204, None)
