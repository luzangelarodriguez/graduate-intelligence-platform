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
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-line bg-[#0B1730] py-5 lg:flex lg:flex-col">
      <div className="mb-6 border-b border-white/10 pb-4 px-4 flex flex-col items-center gap-1">
        <img src={unirLogo} alt="UNIR" style={{ maxWidth: 100, height: 'auto' }} />
        <span style={{ fontSize: 8, fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: '#7B8AAE' }}>
          OBSERVATORIO
        </span>
      </div>

      <nav className="flex flex-col gap-1 px-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg border-l-2 transition text-sm font-medium',
                  isActive
                    ? 'border-brand bg-white/10 text-white'
                    : 'border-transparent text-[#8B9AC0] hover:border-white/20 hover:bg-white/5 hover:text-white',
                ].join(' ')
              }
            >
              <Icon size={17} strokeWidth={1.8} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
