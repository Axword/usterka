import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthService } from 'src/service/auth';
import { errorMessage } from 'src/service/http';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return setErr('Wpisz poprawny adres e-mail.');
    setBusy(true);
    setErr(null);
    try {
      await AuthService.forgotPassword(email.trim());
      setSent(true);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (sent) {
    return (
      <>
        <h1 className="h1">Sprawdź skrzynkę</h1>
        <p className="muted">Jeśli konto z adresem <b>{email.trim()}</b> istnieje, wysłaliśmy na nie link do zmiany hasła. Jest ważny 2 godziny.</p>
        <p className="muted small">Nie ma wiadomości? Zajrzyj do spamu albo spróbuj za kilka minut.</p>
        <p className="small"><Link className="plain" to="/login">← Wróć do logowania</Link></p>
      </>
    );
  }
  return (
    <>
      <h1 className="h1">Zmiana hasła</h1>
      <p className="muted">Podaj adres e-mail konta, a wyślemy link do ustawienia nowego hasła.</p>
      <label className="field"><span className="lbl">Adres e-mail</span>
        <input className="inp" type="email" value={email} autoComplete="email" autoCapitalize="off" spellCheck={false}
          onChange={(e) => setEmail(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} /></label>
      {err && <p className="formerr">{err}</p>}
      <button className="btn primary block" onClick={submit} disabled={busy}>Wyślij link</button>
      <p className="small" style={{ marginTop: 20 }}><Link className="plain" to="/login">← Wróć do logowania</Link></p>
    </>
  );
}
