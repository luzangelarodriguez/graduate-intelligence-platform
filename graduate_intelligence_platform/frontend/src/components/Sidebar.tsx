import { BarChart3, GraduationCap, ShieldCheck, UserRoundCheck } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const items = [
  { to: '/', label: 'Observatorio', icon: BarChart3 },
  { to: '/programas', label: 'Inteligencia curricular', icon: GraduationCap },
  { to: '/gobernanza-fuentes', label: 'Gobernanza de fuentes', icon: ShieldCheck },
  { to: '/registro', label: 'Egresados', icon: UserRoundCheck },
];

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-line bg-white px-4 py-5 lg:block">
      <div className="mb-7 border-b border-line pb-5">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-14 place-items-center bg-ink text-[0.7rem] font-black uppercase tracking-[0.08em] text-white">
            UNIR
          </div>
          <div>
            <strong className="block text-sm font900 text-ink">Colombia</strong>
            <span className="text-[0.72rem] font-semibold uppercase tracking-[0.08em] text-muted">Observatorio</span>
          </div>
        </div>
      </div>

      <nav className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 border-l-2 px-3 py-2.5 text-sm font800 transition',
                  isActive
                    ? 'border-brand bg-slate-50 text-ink'
                    : 'border-transparent text-muted hover:border-line hover:bg-slate-50 hover:text-ink',
                ].join(' ')
              }
            >
              <Icon size={17} strokeWidth={1.8} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="absolute bottom-5 left-4 right-4 border-t border-line pt-4">
        <p className="text-[0.68rem] font900 uppercase tracking-[0.1em] text-muted">Inteligencia curricular</p>
        <p className="mt-2 text-sm font800 leading-5 text-ink">Pertinencia academica y empleabilidad</p>
        <p className="mt-1 text-xs leading-5 text-muted">Analisis institucional de curriculo, demanda laboral y brechas.</p>
      </div>
    </aside>
  );
}
