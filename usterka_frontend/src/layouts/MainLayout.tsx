import { Outlet } from 'react-router-dom';
import VerifyBanner from 'src/components/common/VerifyBanner';

export default function MainLayout() {
  return (
    <>
      <VerifyBanner />
      <Outlet />
    </>
  );
}
