import { Menu, Search } from 'lucide-react';

import { useAuth } from '../context/AuthContext';

interface TopbarProps {
  onMenuClick?: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="lg:hidden btn-ghost p-2 -ml-2"
          onClick={onMenuClick}
          aria-label="Abrir menu"
        >
          <Menu size={20} />
        </button>
        <div className="hidden lg:block">
          <span className="text-sm font-semibold text-ink">Observatorio Curricular</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          className="btn-ghost p-2"
          aria-label="Buscar"
        >
          <Search size={18} strokeWidth={1.5} />
        </button>
        
        <div className="flex items-center gap-3 pl-3 border-l border-line">
          <div className="text-right hidden sm:block">
            <span className="block text-sm font-semibold text-ink">
              {user?.full_name || 'Usuario'}
            </span>
            <span className="block text-xs text-muted">
              {user?.roles?.[0] || 'Observador'}
            </span>
          </div>
          <button
            type="button"
            className="btn btn-secondary text-sm"
            onClick={() => void logout()}
          >
            Salir
          </button>
        </div>
      </div>
    </header>
  );
}
