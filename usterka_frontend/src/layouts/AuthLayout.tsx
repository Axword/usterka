import { Navigate } from 'react-router-dom';
import { useAuth } from 'src/stores/authStore';
import CardLayout from './CardLayout';

export default function AuthLayout() {
  const status = useAuth((s) => s.status);
  if (status === 'ready') return <Navigate to="/" replace />;
  return <CardLayout />;
}
