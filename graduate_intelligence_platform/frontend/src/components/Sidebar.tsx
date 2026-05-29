import {
  BarChart3,
  BookOpen,
  BriefcaseBusiness,
  GitCompare,
  Lightbulb,
  Settings,
  X,
} from 'lucide-react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard Ejecutivo', icon: BarChart3 },
  { to: '/oferta-academica', label: 'Oferta Academica', icon: BookOpen },
  { to: '/mercado-laboral', label: 'Mercado Laboral', icon: BriefcaseBusiness },
  { to: '/brechas-curriculares', label: 'Brechas Curriculares', icon: GitCompare },
  { to: '/recomendaciones', label: 'Recomendaciones IA', icon: Lightbulb },
  { to: '/configuracion', label: 'Configuracion', icon: Settings },
];

interface SidebarProps {
  open?: boolean;
  onClose?: () => void;
}

export function Sidebar({ open = true, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${open ? 'visible' : ''} lg:hidden`}
        onClick={onClose}
      />

      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="unir-brand">
            <div className="unir-brand-logo">UNIR</div>
            <div className="unir-brand-text">
              <span className="unir-brand-title">Colombia</span>
              <span className="unir-brand-subtitle">Observatorio Curricular</span>
            </div>
          </div>
          <button
            type="button"
            className="lg:hidden btn-ghost p-2 -mr-2"
            onClick={onClose}
            aria-label="Cerrar menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav">
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `nav-item ${isActive ? 'active' : ''}`
                  }
                  end={item.to === '/'}
                >
                  <span className="nav-item-icon">
                    <Icon size={18} strokeWidth={1.5} />
                  </span>
                  {item.label}
                </NavLink>
              );
            })}
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="flex items-center gap-2 mb-2">
            <span className="status-dot online" />
            <span className="text-xs font-semibold text-muted">Observatorio activo</span>
          </div>
          <p className="text-xs text-muted leading-relaxed">
            Inteligencia curricular y pertinencia academica para la toma de decisiones.
          </p>
        </div>
      </aside>
    </>
  );
}
