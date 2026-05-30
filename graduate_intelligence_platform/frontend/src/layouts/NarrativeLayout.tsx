import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useState } from 'react';
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Compass,
  Lightbulb,
  Users,
  Menu,
  X,
  GraduationCap,
} from 'lucide-react';

const sections = [
  { id: 'resumen', label: 'Resumen Ejecutivo', icon: BarChart3, path: '/' },
  { id: 'mercado', label: 'Senales del Mercado', icon: TrendingUp, path: '/mercado' },
  { id: 'riesgos', label: 'Observatorio de Riesgos', icon: AlertTriangle, path: '/riesgos' },
  { id: 'futuro', label: 'Futuro del Trabajo', icon: Compass, path: '/futuro' },
  { id: 'recomendaciones', label: 'Centro de Recomendaciones', icon: Lightbulb, path: '/recomendaciones' },
  { id: 'comite', label: 'Espacio Comite Academico', icon: Users, path: '/comite' },
];

export default function NarrativeLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const currentSection = sections.find(s => s.path === location.pathname) || sections[0];

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 bg-white border-b border-line">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
                <GraduationCap className="w-6 h-6 text-white" />
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-semibold text-foreground">Graduate Intelligence</p>
                <p className="text-xs text-muted">Observatorio Curricular UNIR Colombia</p>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-1">
              {sections.map((section) => (
                <NavLink
                  key={section.id}
                  to={section.path}
                  className={({ isActive }) =>
                    `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted hover:text-foreground hover:bg-subtle'
                    }`
                  }
                >
                  {section.label}
                </NavLink>
              ))}
            </nav>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="lg:hidden p-2 rounded-md hover:bg-subtle"
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileOpen && (
          <nav className="lg:hidden border-t border-line bg-white">
            <div className="px-4 py-2 space-y-1">
              {sections.map((section) => (
                <NavLink
                  key={section.id}
                  to={section.path}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md ${
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted hover:text-foreground hover:bg-subtle'
                    }`
                  }
                >
                  <section.icon size={18} />
                  {section.label}
                </NavLink>
              ))}
            </div>
          </nav>
        )}
      </header>

      {/* Section Header */}
      <div className="bg-white border-b border-line">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
              <currentSection.icon className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{currentSection.label}</h1>
              <p className="text-sm text-muted">
                {currentSection.id === 'resumen' && 'Vision integral del estado curricular y alineacion con el mercado'}
                {currentSection.id === 'mercado' && 'Tendencias, senales y dinamicas del mercado laboral'}
                {currentSection.id === 'riesgos' && 'Programas en riesgo y factores de obsolescencia'}
                {currentSection.id === 'futuro' && 'Proyecciones, roles emergentes y trayectorias profesionales'}
                {currentSection.id === 'recomendaciones' && 'Acciones priorizadas por impacto y urgencia'}
                {currentSection.id === 'comite' && 'Evidencia y datos para decisiones academicas'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-[1400px] mx-auto px-4 sm:px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-line bg-white mt-auto">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-4">
          <p className="text-xs text-muted text-center">
            Graduate Intelligence Platform - Observatorio Curricular UNIR Colombia - Datos actualizados en tiempo real
          </p>
        </div>
      </footer>
    </div>
  );
}
