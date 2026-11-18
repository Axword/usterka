import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AuthService } from 'src/service/auth';
import { errorMessage } from 'src/service/http';
import { useAuth } from 'src/stores/authStore';

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const status = useAuth((s) => s.status);
  const refreshMe = useAuth((s) => s.refreshMe);
  const [state, setState] = useState<'work' | 'ok' | string>(token ? 'work' : 'Brak tokenu w linku.');

  useEffect(() => {
    if (!token) return;
    AuthService.verifyEmail(token)
      .then(async () => {
        if (status === 'ready') await refreshMe().catch(() => {});
        setState('ok');
      })
      .catch((e) => setState(errorMessage(e)));
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  const loggedIn = status === 'ready';
  if (state === 'work') return <p className="muted">Potwierdzam adres e-mail…</p>;
  if (state === 'ok') {
    return (
      <>
        <h1 className="h1">Adres potwierdzony</h1>
        <p className="muted">Dziękujemy. Możesz teraz korzystać ze wszystkich funkcji konta.</p>
        <Link className="btn primary block" to={loggedIn ? '/' : '/login'}>{loggedIn ? 'Przejdź do aplikacji' : 'Zaloguj się'}</Link>
      </>
    );
  }
  return (
    <>
      <h1 className="h1">Nie udało się potwierdzić</h1>
      <p className="formerr">{state}</p>
      <Link className="btn block" to={loggedIn ? '/' : '/login'}>{loggedIn ? 'Wróć do aplikacji' : 'Zaloguj się'}</Link>
    </>
  );
}
