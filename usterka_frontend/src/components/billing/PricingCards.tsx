import type { PlanId, PlanInfo } from 'src/types/api';

interface Props {
  plans: PlanInfo[];
  current?: PlanId;
  busy?: boolean;
  onChoose: (plan: PlanId) => void;
  labelFor?: (plan: PlanInfo) => string;
}

const price = (p: PlanInfo) => (p.price_pln === 0 ? '0 zł' : `${p.price_pln} zł`);

export default function PricingCards({ plans, current, busy, onChoose, labelFor }: Props) {
  return (
    <div className="pricing">
      {plans.map((p) => {
        const isCurrent = current === p.id;
        return (
          <article key={p.id} className={`price${p.id === 'pro' ? ' featured' : ''}`}>
            {p.id === 'pro' && <span className="price-tag">Najczęściej wybierany</span>}
            <h3>{p.name}</h3>
            <p className="price-v"><b>{price(p)}</b>{p.price_pln > 0 && <span> / mies. netto</span>}</p>
            <ul>{p.features.map((f) => <li key={f}>{f}</li>)}</ul>
            <button className={`btn block${p.id === 'pro' ? ' primary' : ''}`} disabled={busy || isCurrent} onClick={() => onChoose(p.id)}>
              {isCurrent ? 'Twój obecny plan' : labelFor?.(p) ?? (p.price_pln === 0 ? 'Zacznij za darmo' : `Wybierz ${p.name}`)}
            </button>
          </article>
        );
      })}
    </div>
  );
}
