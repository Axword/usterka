import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from 'src/stores/authStore';

export default function RequireAuth({ children }: { children: ReactNode }) {
  const status = useAuth((s) => s.status);
  const loc = useLocation();
  if (status !== 'ready') return <Navigate to="/welcome" replace state={{ from: loc.pathname }} />;
  return <>{children}</>;
}
