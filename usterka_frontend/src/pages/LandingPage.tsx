import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { BillingService } from 'src/service/billing';
import { useAuth } from 'src/stores/authStore';
import type { PlanInfo } from 'src/types/api';

const STEPS = [
  ['Wgraj plan', 'PDF albo zdjęcie rzutu. Z wielostronicowego PDF-a wybierasz właściwą stronę.'],
  ['Zaznacz usterki', 'Dotknij miejsca na planie, wybierz rodzaj, opisz i zrób zdjęcie. Numer nadaje aplikacja.'],
  ['Zamknij zgłoszenia', 'Gdy wykonawca naprawi, dodajesz zdjęcie „po”. Usterka sama zmienia status.'],
  ['Wydaj protokół', 'PDF lub Word z wycinkami planu i zdjęciami przed i po. Kopia trafia do SharePoint.'],
];

export default function LandingPage() {
  const status = useAuth((s) => s.status);
  const nav = useNavigate();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  useEffect(() => {
    BillingService.plans().then((r) => setPlans(r.plans)).catch(() => {});
  }, []);
  if (status === 'ready') return <Navigate to="/" replace />;

  return (
    <div className="landing">
      <header className="l-head">
        <div className="l-wrap">
          <span className="l-logo"><i />Usterki na planie</span>
          <a className="l-link" href="#jak">Jak to działa</a>
          <a className="l-link" href="#cennik">Cennik</a>
          <Link className="l-btn sm" to="/login">Zaloguj się</Link>
        </div>
      </header>

      <main className="l-wrap">
        <section className="l-hero">
          <div>
            <span className="mono">Odbiory techniczne · lokale · budynki</span>
            <h1>Usterka ma swoje miejsce na planie.</h1>
            <p className="lead">Zamiast listy w arkuszu i zdjęć w telefonie: jeden plan, numerowane pinezki i protokół dla wykonawcy gotowy po obchodzie.</p>
            <div className="l-cta">
              <Link className="l-btn solid" to="/login?mode=register">Załóż konto</Link>
              <a className="l-btn" href="#cennik">Zobacz cennik</a>
            </div>
          </div>
          <figure className="l-fig">
            <img src="/landing-plan.png" alt="Plan lokalu z numerowanymi pinezkami usterek" />
            <figcaption><span className="mono">Plan: Parter – lokal 12</span><span className="mono">6 usterek · 4 otwarte</span></figcaption>
          </figure>
        </section>

        <section id="jak" className="l-sec l-split">
          <div><span className="mono">Przebieg odbioru</span><h2>Od obchodu do protokołu bez przepisywania.</h2></div>
          <ol className="l-rows">
            {STEPS.map(([t, d], i) => (
              <li key={t}><span className="mono">{String(i + 1).padStart(2, '0')}</span><div><h3>{t}</h3><p>{d}</p></div></li>
            ))}
          </ol>
        </section>

        <section id="cennik" className="l-sec">
          <span className="mono">Cennik</span>
          <h2>Płacisz za zespół, nie za usterkę.</h2>
          <div className="l-plans">
            {plans.map((p) => (
              <div key={p.id} className={`l-plan${p.id === 'pro' ? ' pick' : ''}`}>
                <h3>{p.name}</h3>
                <ul>{p.features.map((f) => <li key={f}>{f}</li>)}</ul>
                <div className="cost">{p.price_pln === 0 ? '0 zł' : `${p.price_pln} zł`}{p.price_pln > 0 && <small> / mies. netto</small>}</div>
                <button className={`l-btn${p.id === 'pro' ? ' solid' : ''}`} onClick={() => nav(`/login?mode=register&plan=${p.id}`)}>
                  {p.price_pln === 0 ? 'Zacznij za darmo' : `Wybierz ${p.name}`}
                </button>
              </div>
            ))}
          </div>
          <p className="mono l-note">Plan zmienisz lub anulujesz w dowolnej chwili. Ceny netto.</p>
        </section>
      </main>

      <footer className="l-foot"><div className="l-wrap mono">© {new Date().getFullYear()} Usterki na planie</div></footer>
    </div>
  );
}
