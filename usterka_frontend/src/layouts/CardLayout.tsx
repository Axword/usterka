import { Outlet } from 'react-router-dom';

/** Karta z logo dla stron publicznych (logowanie, reset hasła, zaproszenie), działa też dla zalogowanych. */
export default function CardLayout() {
  return (
    <main className="auth">
      <div className="auth-card">
        <div className="brand">Usterki na planie</div>
        <Outlet />
      </div>
    </main>
  );
}
