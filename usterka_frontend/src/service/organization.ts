import { rest } from './rest';
import type { Invitation, Member, Organization, Role } from 'src/types/api';

export const OrganizationService = {
  get: () => rest.get<Organization>('organization/'),
  update: (data: Partial<Omit<Organization, 'id' | 'sharepoint_configured'>>) => rest.patch<Organization>('organization/', data),
  members: () => rest.get<Member[]>('organization/members'),
  removeMember: (id: number) => rest.delete(`organization/members/${id}`),
  invitations: () => rest.get<Invitation[]>('organization/invitations'),
  invite: (email: string, role: Role) => rest.post<Invitation>('organization/invitations', { email, role }),
  revokeInvitation: (id: string) => rest.delete(`organization/invitations/${id}`),
  setRole: (id: number, role: Role) => rest.patch<Member>(`organization/members/${id}`, { role }),
};
