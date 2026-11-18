import { create } from 'zustand';
import { DefectService } from 'src/service/defect';
import { OrganizationService } from 'src/service/organization';
import { PlanService } from 'src/service/plan';
import { ProjectService } from 'src/service/project';
import type { Defect, Organization, Plan, Project } from 'src/types/api';

/** Bieżąca inwestycja: dane, plany i usterki (wzorem lol_spy/stores/teamStore.js). */
interface ProjectState {
  project: Project | null;
  plans: Plan[];
  defects: Defect[];
  organization: Organization | null;
  loading: boolean;
  load: (projectId: string) => Promise<void>;
  loadOrganization: () => Promise<Organization>;
  refreshProject: () => Promise<void>;
  setProject: (p: Project) => void;
  upsertDefect: (d: Defect) => void;
  removeDefect: (id: string) => void;
  upsertPlan: (p: Plan) => void;
  removePlan: (id: string) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  project: null,
  plans: [],
  defects: [],
  organization: null,
  loading: false,

  async load(projectId) {
    if (get().project?.id !== projectId) set({ project: null, plans: [], defects: [] });
    set({ loading: true });
    try {
      const [project, plans, defects] = await Promise.all([
        ProjectService.get(projectId),
        PlanService.list(projectId),
        DefectService.list(projectId),
      ]);
      set({ project, plans, defects });
      if (!get().organization) await get().loadOrganization();
    } finally {
      set({ loading: false });
    }
  },

  async loadOrganization() {
    const organization = await OrganizationService.get();
    set({ organization });
    return organization;
  },

  async refreshProject() {
    const p = get().project;
    if (p) set({ project: await ProjectService.get(p.id) });
  },

  setProject: (project) => set({ project }),
  upsertDefect: (d) =>
    set((s) => ({
      defects: [...s.defects.filter((x) => x.id !== d.id), d].sort((a, b) => a.no - b.no),
    })),
  removeDefect: (id) => set((s) => ({ defects: s.defects.filter((d) => d.id !== id) })),
  upsertPlan: (p) =>
    set((s) => ({
      plans: s.plans.some((x) => x.id === p.id) ? s.plans.map((x) => (x.id === p.id ? p : x)) : [...s.plans, p],
    })),
  removePlan: (id) =>
    set((s) => ({ plans: s.plans.filter((p) => p.id !== id), defects: s.defects.filter((d) => d.plan_id !== id) })),
}));
