import { useState } from 'react';
import { AuthService } from 'src/service/auth';
import { errorMessage } from 'src/service/http';
import { useAuth } from 'src/stores/authStore';
import { toast } from 'src/stores/uiStore';

/** Pasek dla kont z niepotwierdzonym adresem e-mail (Microsoft i zaproszone osoby są potwierdzone od razu). */
export default function VerifyBanner() {
  const me = useAuth((s) => s.me);
  const [busy, setBusy] = useState(false);
  if (!me || me.email_verified) return null;

  const resend = async () => {
    setBusy(true);
    try {
      await AuthService.resendVerification();
      toast(`Wysłaliśmy link na ${me.email}`);
    } catch (e) {
      toast(errorMessage(e), 5000);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="verify-banner" role="status">
      <span>Potwierdź adres e-mail (<b>{me.email}</b>), klikając link z wiadomości.</span>
      <button className="btn small" onClick={resend} disabled={busy}>Wyślij ponownie</button>
    </div>
  );
}
