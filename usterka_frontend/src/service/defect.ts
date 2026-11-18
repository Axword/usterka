import { rest } from './rest';
import type { Defect, DefectEvent, DefectInput, PhotoKind } from 'src/types/api';

export const DefectService = {
  list: (projectId: string, params?: { plan_id?: string; status?: string }) =>
    rest.get<Defect[]>(`projects/${projectId}/defects`, params),
  get: (id: string) => rest.get<Defect>(`defects/${id}`),
  create: (projectId: string, data: DefectInput) => rest.post<Defect>(`projects/${projectId}/defects`, data),
  update: (id: string, data: Partial<DefectInput>) => rest.patch<Defect>(`defects/${id}`, data),
  remove: (id: string) => rest.delete(`defects/${id}`),
  events: (id: string) => rest.get<DefectEvent[]>(`defects/${id}/events`),
  addPhoto: (id: string, kind: PhotoKind, file: Blob) => {
    const f = new FormData();
    f.append('kind', kind);
    f.append('file', file, 'photo.jpg');
    return rest.upload<Defect>(`defects/${id}/photos`, f);
  },
  removePhoto: (photoId: string) => rest.delete<Defect>(`photos/${photoId}`),
  photoUrl: (photoId: string) => `photos/${photoId}/file`,
  types: () => rest.get<string[]>('defect-types'),
};
