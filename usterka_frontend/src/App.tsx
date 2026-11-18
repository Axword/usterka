import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import UiHost from './components/common/UiHost';
import { router } from './router';
import { setUnauthorizedHandler } from './service/httpAuth';
import { useAuth } from './stores/authStore';

export default function App() {
  const { status, init } = useAuth();
  useEffect(() => {
    init();
    setUnauthorizedHandler(() => {
      useAuth.setState({ me: null, status: 'anonymous' });
      router.navigate('/login');
    });
  }, [init]);

  if (status === 'loading') {
    return <div className="busy"><div><div className="spin" /><div>Ładowanie…</div></div></div>;
  }
  return (
    <>
      <RouterProvider router={router} />
      <UiHost />
    </>
  );
}
