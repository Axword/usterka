export type Role = 'admin' | 'inspector' | 'viewer';

export interface AuthConfig {
  dev_login: boolean;
  password_login: boolean;
  microsoft: boolean;
  client_id: string;
  tenant: string;
  api_scope: string;
}

export interface Me {
  id: number;
  email: string;
  display_name: string;
  microsoft: boolean;
  organization_id: string;
  organization_name: string;
  role: Role;
}

export interface Organization {
  id: string;
  name: string;
  defect_types: string[];
  sp_site_url: string;
  sp_library: string;
  sp_folder: string;
  sharepoint_configured: boolean;
}

export interface Member {
  id: number;
  email: string;
  display_name: string;
  role: Role;
}

export type DefectFilter = 'all' | 'open' | 'fixed';

export interface ReportSettings {
  date: string | null;
  filter: DefectFilter;
  plans: boolean;
  logo: boolean;
  sharepoint: boolean;
}

export interface Project {
  id: string;
  name: string;
  address: string;
  investor: string;
  contractor: string;
  inspection_date: string | null;
  author: string;
  has_logo: boolean;
  is_complete: boolean;
  report_settings: Partial<ReportSettings>;
  plans_count: number;
  open_count: number;
  fixed_count: number;
  created_at: string;
  updated_at: string;
}

export type ProjectInput = Pick<Project, 'name' | 'address' | 'investor' | 'contractor' | 'inspection_date' | 'author'>;

export interface Plan {
  id: string;
  project_id: string;
  name: string;
  width: number;
  height: number;
  source_filename: string;
  source_page: number | null;
  created_at: string;
}

export type PhotoKind = 'before' | 'after';

export interface Photo {
  id: string;
  kind: PhotoKind;
  width: number;
  height: number;
}

export type DueMode = 'umowa' | 'data';

export interface Defect {
  id: string;
  project_id: string;
  plan_id: string;
  no: number;
  x: number;
  y: number;
  type: string;
  type_other: string;
  description: string;
  due_mode: DueMode;
  due_date: string | null;
  status: 'open' | 'fixed';
  fixed_date: string | null;
  zoom: number;
  photos: Photo[];
  created_at: string;
  updated_at: string;
}

export interface DefectInput {
  id?: string;
  plan_id: string;
  x: number;
  y: number;
  type: string;
  type_other: string;
  description: string;
  due_mode: DueMode;
  due_date: string | null;
  zoom: number;
  fixed_date?: string | null;
}

export interface DefectEvent {
  action: string;
  changes: Record<string, unknown>;
  user: string;
  created_at: string;
}

export interface Report {
  id: string;
  project_id: string;
  kind: 'pdf' | 'docx';
  filename: string;
  size: number;
  document_date: string;
  defect_filter: DefectFilter;
  defects_count: number;
  created_by: string;
  created_at: string;
  sharepoint_status: 'none' | 'ok' | 'error';
  sharepoint_url: string;
  sharepoint_path: string;
  sharepoint_error: string;
}

export type PlanId = 'free' | 'pro' | 'business';

export interface PlanInfo {
  id: PlanId;
  name: string;
  price_pln: number;
  max_projects: number | null;
  max_members: number | null;
  features: string[];
}

export interface PlansResponse {
  plans: PlanInfo[];
  payments_enabled: boolean;
  demo_mode: boolean;
}

export interface Subscription {
  plan: PlanId;
  plan_name: string;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  is_demo: boolean;
  has_customer: boolean;
  projects_used: number;
  projects_limit: number | null;
}
