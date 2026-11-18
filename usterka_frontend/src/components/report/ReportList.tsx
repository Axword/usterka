import { useEffect, useState } from 'react';
import { fileBlob } from 'src/service/files';
import { errorMessage } from 'src/service/http';
import { ReportService } from 'src/service/report';
import { useAuth } from 'src/stores/authStore';
import { toast, withBusy } from 'src/stores/uiStore';
import type { Report } from 'src/types/api';
import { fmtDate } from 'src/utils/dates';
import { downloadBlob } from 'src/utils/download';

const FILTER = { all: 'wszystkie', open: 'otwarte', fixed: 'usunięte' };

export default function ReportList({ projectId, version }: { projectId: string; version: number }) {
  const [reports, setReports] = useState<Report[]>([]);
  const canWrite = useAuth((s) => s.canWrite());
  useEffect(() => {
    ReportService.list(projectId).then(setReports).catch(() => {});
  }, [projectId, version]);
  if (!reports.length) return null;

  const download = async (r: Report) => {
    try {
      downloadBlob(r.filename, await withBusy('Pobieranie…', () => fileBlob(ReportService.fileUrl(r.id))));
    } catch (e) {
      toast(errorMessage(e));
    }
  };
  const retry = async (r: Report) => {
    try {
      const n = await withBusy('Zapisywanie w SharePoint…', () => ReportService.retrySharepoint(r.id));
      setReports((rs) => rs.map((x) => (x.id === n.id ? n : x)));
      toast(n.sharepoint_status === 'ok' ? 'Zapisano w SharePoint' : n.sharepoint_error, 5000);
    } catch (e) {
      toast(errorMessage(e));
    }
  };

  return (
    <section className="backup">
      <h2 className="h2">Historia raportów <span className="n">{reports.length}</span></h2>
      <ul className="dlist">
        {reports.map((r) => (
          <li key={r.id} className="ritem">
            <div className="txt">
              <span className="ty">{r.kind.toUpperCase()} z {fmtDate(r.document_date)}</span>
              <span className="muted small">
                {new Date(r.created_at).toLocaleString('pl-PL')} · {r.created_by} · usterki: {r.defects_count} ({FILTER[r.defect_filter]})
              </span>
              {r.sharepoint_status === 'ok' && <a className="small" href={r.sharepoint_url} target="_blank" rel="noreferrer">Otwórz w SharePoint</a>}
              {r.sharepoint_status === 'error' && <span className="ferr">SharePoint: {r.sharepoint_error}</span>}
            </div>
            <div className="row">
              <button className="btn small" onClick={() => download(r)}>Pobierz</button>
              {canWrite && r.sharepoint_status !== 'ok' && <button className="btn small" onClick={() => retry(r)}>Do SharePoint</button>}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
