import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { errorMessage } from 'src/service/http';
import { useAuth } from 'src/stores/authStore';
import { toast } from 'src/stores/uiStore';

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const uid = params.get('uid') ?? '';
  const token = params.get('token') ?? '';
  const resetPassword = useAuth((s) => s.resetPassword);
  const nav = useNavigate();
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!uid || !token) {
    return (
      <>
        <h1 className="h1">Nieprawidłowy link</h1>
        <p className="muted">Link do zmiany hasła jest niepełny. Poproś o nowy.</p>
        <Link className="btn block" to="/forgot">Poproś o nowy link</Link>
      </>
    );
  }

  const submit = async () => {
    if (password.length < 8) return setErr('Hasło musi mieć co najmniej 8 znaków.');
    if (password !== repeat) return setErr('Hasła nie są takie same.');
    setBusy(true);
    setErr(null);
    try {
      await resetPassword(uid, token, password);
      toast('Hasło zmienione. Jesteś zalogowany.');
      nav('/', { replace: true });
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1 className="h1">Nowe hasło</h1>
      <label className="field"><span className="lbl">Nowe hasło</span>
        <input className="inp" type="password" value={password} autoComplete="new-password" placeholder="Minimum 8 znaków"
          onChange={(e) => setPassword(e.target.value)} /></label>
      <label className="field"><span className="lbl">Powtórz hasło</span>
        <input className="inp" type="password" value={repeat} autoComplete="new-password"
          onChange={(e) => setRepeat(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} /></label>
      {err && <p className="formerr">{err} {err.includes('Link') && <Link className="plain" to="/forgot">Poproś o nowy.</Link>}</p>}
      <button className="btn primary block" onClick={submit} disabled={busy}>Zapisz hasło</button>
    </>
  );
}
