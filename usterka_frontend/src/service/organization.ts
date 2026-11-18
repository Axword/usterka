import { rest } from './rest';
import type { Member, Organization, Role } from 'src/types/api';

export const OrganizationService = {
  get: () => rest.get<Organization>('organization/'),
  update: (data: Partial<Omit<Organization, 'id' | 'sharepoint_configured'>>) => rest.patch<Organization>('organization/', data),
  members: () => rest.get<Member[]>('organization/members'),
  setRole: (id: number, role: Role) => rest.patch<Member>(`organization/members/${id}`, { role }),
};
