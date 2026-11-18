import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AuthService } from 'src/service/auth';
import { errorMessage } from 'src/service/http';
import { useAuth } from 'src/stores/authStore';
import { toast } from 'src/stores/uiStore';
import type { InvitationInfo } from 'src/types/api';

const ROLE_NAMES = { admin: 'administrator', inspector: 'inspektor', viewer: 'osoba z podglądem' } as const;

export default function InvitePage() {
  const { token = '' } = useParams();
  const acceptInvitation = useAuth((s) => s.acceptInvitation);
  const nav = useNavigate();
  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    AuthService.invitation(token).then(setInfo).catch((e) => setLoadErr(errorMessage(e)));
  }, [token]);

  if (loadErr) {
    return (
      <>
        <h1 className="h1">Zaproszenie nieaktywne</h1>
        <p className="formerr">{loadErr}</p>
        <p className="muted small">Poproś osobę, która Cię zaprosiła, o nowe zaproszenie.</p>
        <Link className="btn block" to="/login">Przejdź do logowania</Link>
      </>
    );
  }
  if (!info) return <p className="muted">Wczytywanie zaproszenia…</p>;

  const submit = async () => {
    if (password.length < 8) return setErr('Hasło musi mieć co najmniej 8 znaków.');
    setBusy(true);
    setErr(null);
    try {
      await acceptInvitation(token, password, name);
      toast(`Witaj w zespole „${info.organization_name}”`);
      nav('/', { replace: true });
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1 className="h1">Dołącz do zespołu</h1>
      <p className="muted">Zaproszono Cię do <b>{info.organization_name}</b> jako {ROLE_NAMES[info.role]}. Załóż hasło do konta <b>{info.email}</b>.</p>
      <label className="field"><span className="lbl">Imię i nazwisko</span>
        <input className="inp" value={name} autoComplete="name" onChange={(e) => setName(e.target.value)} /></label>
      <label className="field"><span className="lbl">Hasło</span>
        <input className="inp" type="password" value={password} autoComplete="new-password" placeholder="Minimum 8 znaków"
          onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} /></label>
      {err && <p className="formerr">{err}</p>}
      <button className="btn primary block" onClick={submit} disabled={busy}>Utwórz konto i dołącz</button>
    </>
  );
}
