import { Outlet } from 'react-router-dom';

import { Topbar } from '../components/Topbar';
import { Sidebar } from '../components/Sidebar';

export function AppLayout() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <Topbar />
      <Sidebar />
      <main className="mx-auto max-w-[1440px] px-4 pb-8 pt-4 sm:px-6 lg:pl-[17rem] lg:pr-7">
        <Outlet />
      </main>
    </div>
  );
}
