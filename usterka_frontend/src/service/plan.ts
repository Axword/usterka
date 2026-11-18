import { rest } from './rest';
import type { Plan } from 'src/types/api';

export const PlanService = {
  list: (projectId: string) => rest.get<Plan[]>(`projects/${projectId}/plans`),
  create: (projectId: string, p: { name: string; image: Blob; sourceFilename?: string; sourcePage?: number | null }, onProgress?: (x: number) => void) => {
    const f = new FormData();
    f.append('name', p.name);
    f.append('source_filename', p.sourceFilename || '');
    if (p.sourcePage) f.append('source_page', String(p.sourcePage));
    f.append('image', p.image, 'plan.jpg');
    return rest.upload<Plan>(`projects/${projectId}/plans`, f, onProgress);
  },
  rename: (id: string, name: string) => rest.patch<Plan>(`plans/${id}`, { name }),
  remove: (id: string) => rest.delete(`plans/${id}`),
  imageUrl: (id: string) => `plans/${id}/image`,
};
