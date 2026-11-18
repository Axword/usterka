import Http from './http';
import { rest } from './rest';
import type { PlanId, PlansResponse, Subscription } from 'src/types/api';

const anon = new Http();

export const BillingService = {
  plans: async () => (await anon.http.get<PlansResponse>('billing/plans')).data,
  subscription: () => rest.get<Subscription>('billing/subscription'),
  checkout: (plan: Exclude<PlanId, 'free'>) => rest.post<{ url: string | null; activated: boolean }>('billing/checkout', { plan }),
  portal: () => rest.post<{ url: string }>('billing/portal'),
  downgrade: () => rest.post<Subscription>('billing/downgrade'),
};
