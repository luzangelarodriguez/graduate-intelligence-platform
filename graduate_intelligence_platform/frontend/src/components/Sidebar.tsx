import { BarChart3, GraduationCap, UserRoundCheck } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import unirLogo from '../assets/logos/UNIR_v_blanco.png';

const items = [
  { to: '/', label: 'Observatorio', icon: BarChart3 },
  { to: '/programas', label: 'Inteligencia curricular', icon: GraduationCap },
  { to: '/registro', label: 'Egresados', icon: UserRoundCheck },
];

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-16 border-r border-line bg-white py-5 lg:flex lg:flex-col lg:items-center">
      <div className="mb-6 border-b border-line pb-4 w-full flex justify-center">
        <img src={unirLogo} alt="UNIR" style={{ maxWidth: 36, height: 'auto' }} />
      </div>

      <nav className="flex flex-col items-center gap-1 w-full px-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              title={item.label}
              className={({ isActive }) =>
                [
                  'flex items-center justify-center w-10 h-10 rounded-lg border-l-2 transition',
                  isActive
                    ? 'border-brand bg-slate-50 text-ink'
                    : 'border-transparent text-muted hover:border-line hover:bg-slate-50 hover:text-ink',
                ].join(' ')
              }
            >
              <Icon size={17} strokeWidth={1.8} />
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
