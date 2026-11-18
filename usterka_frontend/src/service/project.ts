import { rest } from './rest';
import type { Project, ProjectInput, ReportSettings } from 'src/types/api';

const URL = 'projects/';

export const ProjectService = {
  list: () => rest.get<Project[]>(URL),
  get: (id: string) => rest.get<Project>(`${URL}${id}`),
  create: (data: ProjectInput) => rest.post<Project>(URL, data),
  update: (id: string, data: Partial<ProjectInput>) => rest.patch<Project>(`${URL}${id}`, data),
  remove: (id: string) => rest.delete(`${URL}${id}`),
  saveReportSettings: (id: string, s: ReportSettings) => rest.put<Project>(`${URL}${id}/report-settings`, s),
  uploadLogo: (id: string, file: Blob) => {
    const f = new FormData();
    f.append('file', file, 'logo.png');
    return rest.upload<Project>(`${URL}${id}/logo`, f);
  },
  removeLogo: (id: string) => rest.delete<Project>(`${URL}${id}/logo`),
  logoUrl: (id: string) => `${URL}${id}/logo`,
};
