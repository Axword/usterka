import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import PricingCards from 'src/components/billing/PricingCards';
import { BackIcon } from 'src/components/common/Icons';
import { BillingService } from 'src/service/billing';
import { errorMessage } from 'src/service/http';
import { useAuth } from 'src/stores/authStore';
import { toast, withBusy } from 'src/stores/uiStore';
import type { PlanId, PlansResponse, Subscription } from 'src/types/api';
import { fmtDate } from 'src/utils/dates';

export default function SubscriptionPage() {
  const isAdmin = useAuth((s) => s.me?.role === 'admin');
  const [params, setParams] = useSearchParams();
  const [plans, setPlans] = useState<PlansResponse | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);

  const reload = () => BillingService.subscription().then(setSub).catch((e) => toast(errorMessage(e)));
  useEffect(() => {
    BillingService.plans().then(setPlans).catch(() => {});
    reload();
    if (params.get('paid')) {
      toast('Dziękujemy! Płatność przetwarzamy, plan zmieni się za chwilę.', 5000);
      setParams({}, { replace: true });
      setTimeout(reload, 2500);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const choose = async (plan: PlanId) => {
    if (plan === 'free') return;
    try {
      const r = await withBusy('Przechodzę do płatności…', () => BillingService.checkout(plan));
      if (r.url) window.location.href = r.url;
      else if (r.activated) { toast('Plan zmieniony (tryb demo, bez płatności).'); reload(); }
    } catch (e) {
      toast(errorMessage(e), 5000);
    }
  };

  const manage = async () => {
    try {
      if (sub?.is_demo) { setSub(await BillingService.downgrade()); toast('Wrócono do planu Start.'); return; }
      const { url } = await withBusy('Otwieram portal płatności…', () => BillingService.portal());
      window.location.href = url;
    } catch (e) {
      toast(errorMessage(e), 5000);
    }
  };

  const usage = sub && sub.projects_limit ? Math.min(100, Math.round((sub.projects_used / sub.projects_limit) * 100)) : 0;

  return (
    <>
      <header className="bar">
        <Link className="back" to="/"><BackIcon />Inwestycje</Link>
        <h1 className="bar-t">Subskrypcja</h1>
      </header>
      <main className="wrap">
        {sub && (
          <section className="subcard">
            <div>
              <span className="muted small">Twój plan</span>
              <h2 className="h1">{sub.plan_name}</h2>
              {sub.current_period_end && sub.plan !== 'free' && (
                <p className="muted small">{sub.cancel_at_period_end ? 'Wygasa' : 'Odnawia się'} {fmtDate(sub.current_period_end.slice(0, 10))}</p>
              )}
              {sub.is_demo && <p className="note">Tryb demo: plan włączony bez prawdziwej płatności.</p>}
            </div>
            <div className="usage">
              <span className="small">Inwestycje: <b>{sub.projects_used}</b> / {sub.projects_limit ?? '∞'}</span>
              {sub.projects_limit && <div className="bar-track"><div className="bar-fill" style={{ width: `${usage}%` }} /></div>}
              {isAdmin && sub.plan !== 'free' && <button className="btn small" onClick={manage}>{sub.is_demo ? 'Wróć do planu Start' : 'Zarządzaj płatnościami'}</button>}
            </div>
          </section>
        )}
        {!isAdmin && <p className="note">Plan zmienia administrator organizacji.</p>}
        <h2 className="h2">Dostępne plany</h2>
        {plans && sub && <PricingCards plans={plans.plans} current={sub.plan} busy={!isAdmin} onChoose={choose}
          labelFor={(p) => (p.id === 'free' ? 'Plan podstawowy' : `Przejdź na ${p.name}`)} />}
        {plans?.demo_mode && <p className="muted small">Płatności nie są skonfigurowane (Stripe), więc zakup jest symulowany.</p>}
      </main>
    </>
  );
}
