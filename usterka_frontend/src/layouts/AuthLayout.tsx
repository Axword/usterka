import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from 'src/stores/authStore';

export default function AuthLayout() {
  const status = useAuth((s) => s.status);
  if (status === 'ready') return <Navigate to="/" replace />;
  return (
    <main className="auth">
      <div className="auth-card">
        <div className="brand">Usterki na planie</div>
        <Outlet />
      </div>
    </main>
  );
}
