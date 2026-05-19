import { Menu, Search } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import unirLogo from '../assets/logos/unir-logo.svg';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { to: '/', label: 'Observatorio' },
  { to: '/programas', label: 'Inteligencia curricular' },
  { to: '/gobernanza-fuentes', label: 'Gobernanza de fuentes' },
  { to: '/registro', label: 'Egresados' },
];

export function Topbar() {
  const { user, logout } = useAuth();

  return (
    <header className="unir-header">
      <div className="unir-topbar">
        <div className="unir-topbar-inner">
          <img className="unir-logo" src={unirLogo} alt="UNIR - La Universidad en Internet" />
          <div className="unir-platform-title">
            <span>UNIR Colombia</span>
            <strong>Observatorio institucional de inteligencia curricular</strong>
          </div>
          <div className="unir-session">
            <span>{user?.full_name}</span>
            <button type="button" onClick={() => void logout()}>
              Salir
            </button>
          </div>
        </div>
      </div>

      <nav className="unir-blackbar">
        <div className="unir-blackbar-inner">
          <button className="unir-menu-button" type="button" aria-label="MenÃº institucional">
            <Menu size={18} strokeWidth={1.8} />
            MenÃº
          </button>
          <div className="unir-nav-links">
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
                {item.label}
              </NavLink>
            ))}
          </div>
          <button className="unir-search-button" type="button" aria-label="Buscar">
            <Search size={17} strokeWidth={1.8} />
          </button>
        </div>
      </nav>
    </header>
  );
}

