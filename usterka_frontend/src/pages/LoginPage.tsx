import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { errorMessage } from 'src/service/http';
import { useAuth } from 'src/stores/authStore';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const { config, devLogin, passwordLogin, register, microsoftLogin, error } = useAuth();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const mode = params.get('mode') === 'register' ? 'register' : 'login';
  const [f, setF] = useState({ email: '', password: '', name: '', company: '' });
  const [err, setErr] = useState<string | null>(error);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      nav(params.get('plan') && mode === 'register' ? '/subscription' : '/', { replace: true });
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const submit = () => {
    if (!EMAIL_RE.test(f.email.trim())) return setErr('Wpisz poprawny adres e-mail.');
    if (mode === 'register') {
      if (f.password.length < 8) return setErr('Hasło musi mieć co najmniej 8 znaków.');
      return run(() => register({ email: f.email.trim(), password: f.password, name: f.name, company: f.company }));
    }
    if (!f.password) return setErr('Wpisz hasło.');
    return run(() => passwordLogin(f.email.trim(), f.password));
  };

  const ms = async () => {
    setBusy(true);
    try {
      await microsoftLogin();
    } catch (e) {
      setErr(errorMessage(e));
      setBusy(false);
    }
  };

  if (!config) return <p className="formerr">Brak połączenia z serwerem. Sprawdź, czy backend działa.</p>;
  const enter = (e: React.KeyboardEvent) => e.key === 'Enter' && submit();

  return (
    <>
      {config.password_login && (
        <>
          <div className="seg mt" role="tablist" style={{ marginBottom: 20 }}>
            <button role="tab" aria-pressed={mode === 'login'} onClick={() => setParams({})}>Logowanie</button>
            <button role="tab" aria-pressed={mode === 'register'} onClick={() => setParams({ mode: 'register' })}>Załóż konto</button>
          </div>
          {mode === 'register' && (
            <>
              <label className="field"><span className="lbl">Imię i nazwisko</span>
                <input className="inp" value={f.name} autoComplete="name" onChange={set('name')} /></label>
              <label className="field"><span className="lbl">Nazwa firmy</span>
                <input className="inp" value={f.company} autoComplete="organization" onChange={set('company')} /></label>
            </>
          )}
          <label className="field"><span className="lbl">Adres e-mail</span>
            <input className="inp" type="email" value={f.email} autoComplete="email" autoCapitalize="off" spellCheck={false}
              placeholder="imie.nazwisko@firma.pl" onChange={set('email')} onKeyDown={enter} /></label>
          <label className="field"><span className="lbl">Hasło</span>
            <input className="inp" type="password" value={f.password} onChange={set('password')} onKeyDown={enter}
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'} placeholder={mode === 'register' ? 'Minimum 8 znaków' : ''} /></label>
          {err && <p className="formerr">{err}</p>}
          <button className="btn primary block" onClick={submit} disabled={busy}>{mode === 'register' ? 'Utwórz konto' : 'Zaloguj się'}</button>
        </>
      )}

      {config.microsoft && (
        <section className={config.password_login ? 'alt' : ''}>
          <button className="btn block" onClick={ms} disabled={busy}>Zaloguj kontem Microsoft</button>
        </section>
      )}

      {config.dev_login && mode === 'login' && (
        <section className="alt">
          <div className="demo">Tryb deweloperski: logowanie samym e-mailem, bez hasła. Wyłączone na produkcji.</div>
          <button className="btn block" disabled={busy || !EMAIL_RE.test(f.email.trim())}
            onClick={() => run(() => devLogin(f.email.trim()))}>Zaloguj (dev) jako {f.email.trim() || 'wpisany e-mail'}</button>
        </section>
      )}

      {!config.microsoft && !config.dev_login && !config.password_login && <p className="formerr">Logowanie nie jest skonfigurowane na serwerze.</p>}
      {err && !config.password_login && <p className="formerr">{err}</p>}
      <p className="small" style={{ marginTop: 20 }}><Link className="plain" to="/welcome">← Wróć na stronę główną</Link></p>
    </>
  );
}
