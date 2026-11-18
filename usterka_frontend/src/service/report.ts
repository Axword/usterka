import { rest } from './rest';
import type { DefectFilter, Report } from 'src/types/api';

export const ReportService = {
  list: (projectId: string) => rest.get<Report[]>(`projects/${projectId}/reports`),
  create: (
    projectId: string,
    r: { kind: 'pdf' | 'docx'; documentDate: string; filter: DefectFilter; count: number; sharepoint: boolean; file: Blob },
    onProgress?: (p: number) => void,
  ) => {
    const f = new FormData();
    f.append('kind', r.kind);
    f.append('document_date', r.documentDate);
    f.append('defect_filter', r.filter);
    f.append('defects_count', String(r.count));
    f.append('send_to_sharepoint', r.sharepoint ? 'true' : 'false');
    f.append('file', r.file, `raport.${r.kind}`);
    return rest.upload<Report>(`projects/${projectId}/reports`, f, onProgress);
  },
  retrySharepoint: (id: string) => rest.post<Report>(`reports/${id}/sharepoint`),
  remove: (id: string) => rest.delete(`reports/${id}`),
  fileUrl: (id: string) => `reports/${id}/file`,
};
