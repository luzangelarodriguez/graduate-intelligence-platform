import { useState, useEffect } from 'react';
import {
  TrendingUp,
  Briefcase,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  Users,
  Zap,
  Lightbulb,
  Menu,
  X,
} from 'lucide-react';
import { EstadoSection } from '../components/observatory/EstadoSection';
import { MercadoSection } from '../components/observatory/MercadoSection';
import { ProgramaSection } from '../components/observatory/ProgramaSection';
import { CoberturaSection } from '../components/observatory/CoberturaSection';
import { BrechasSection } from '../components/observatory/BrechasSection';
import { EmpleosSection } from '../components/observatory/EmpleosSection';
import { SimulacionSection } from '../components/observatory/SimulacionSection';
import { RecomendacionesSection } from '../components/observatory/RecomendacionesSection';

interface NavigationItem {
  id: string;
  label: string;
  icon: typeof TrendingUp;
  section: string;
}

const navigationItems: NavigationItem[] = [
  { id: 'estado', label: 'Estado de Pertinencia', icon: TrendingUp, section: 'estado' },
  { id: 'mercado', label: 'Qué Demanda Mercado', icon: Briefcase, section: 'mercado' },
  { id: 'programa', label: 'Qué Enseña Programa', icon: BookOpen, section: 'programa' },
  { id: 'cobertura', label: 'Cobertura Curricular', icon: CheckCircle2, section: 'cobertura' },
  { id: 'brechas', label: 'Brechas Identificadas', icon: AlertCircle, section: 'brechas' },
  { id: 'empleos', label: 'Empleos Compatibles', icon: Users, section: 'empleos' },
  { id: 'simulacion', label: 'Simulación Mejora', icon: Zap, section: 'simulacion' },
  { id: 'recomendaciones', label: 'Recomendaciones', icon: Lightbulb, section: 'recomendaciones' },
];

export function ObservatorioMinimalista() {
  const [activeSection, setActiveSection] = useState('estado');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState('Ingeniería de Sistemas');

  const scrollToSection = (sectionId: string) => {
    setActiveSection(sectionId);
    setSidebarOpen(false);
    const element = document.getElementById(`section-${sectionId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="flex h-screen bg-[var(--color-background)]">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:w-60 lg:flex-col lg:border-r lg:border-[var(--color-border)] lg:bg-[var(--color-navy)]">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          {/* Logo Section */}
          <div className="mb-8 pb-6 border-b border-[var(--color-navy-light)]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-12 items-center justify-center bg-white text-xs font-black text-[var(--color-navy)]">
                UNIR
              </div>
              <div>
                <p className="text-sm font-bold text-white">Colombia</p>
                <p className="text-xs font-semibold text-gray-300">Observatorio</p>
              </div>
            </div>
          </div>

          {/* Program Selector */}
          <div className="mb-8">
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300">
              Programa
            </label>
            <select
              value={selectedProgram}
              onChange={(e) => setSelectedProgram(e.target.value)}
              className="mt-2 w-full rounded border border-[var(--color-navy-light)] bg-[var(--color-navy-light)] px-3 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-red)]"
            >
              <option>Ingeniería de Sistemas</option>
              <option>Administración de Empresas</option>
              <option>Contabilidad</option>
            </select>
          </div>

          {/* Navigation */}
          <nav className="space-y-1">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => scrollToSection(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-600 rounded transition-all ${
                    isActive
                      ? 'bg-[var(--color-accent-red)] text-white'
                      : 'text-gray-200 hover:bg-[var(--color-navy-light)] hover:text-white'
                  }`}
                >
                  <Icon size={18} strokeWidth={1.5} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer Info */}
        <div className="border-t border-[var(--color-navy-light)] px-4 py-4">
          <p className="text-xs font-bold uppercase tracking-widest text-gray-300">
            Inteligencia Curricular
          </p>
          <p className="mt-2 text-xs leading-relaxed text-gray-200">
            Análisis integral de pertinencia y empleabilidad
          </p>
        </div>
      </aside>

      {/* Mobile Hamburger */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-4 left-4 z-40 lg:hidden p-2 rounded-lg bg-[var(--color-navy)] text-white"
      >
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-30 w-60 bg-[var(--color-navy)] overflow-y-auto transition-transform lg:hidden ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full px-4 py-6">
          {/* Logo Section */}
          <div className="mb-8 pb-6 border-b border-[var(--color-navy-light)]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-12 items-center justify-center bg-white text-xs font-black text-[var(--color-navy)]">
                UNIR
              </div>
              <div>
                <p className="text-sm font-bold text-white">Colombia</p>
                <p className="text-xs font-semibold text-gray-300">Observatorio</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => scrollToSection(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-600 rounded transition-all ${
                    isActive
                      ? 'bg-[var(--color-accent-red)] text-white'
                      : 'text-gray-200 hover:bg-[var(--color-navy-light)] hover:text-white'
                  }`}
                >
                  <Icon size={18} strokeWidth={1.5} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          {/* Header */}
          <header className="mb-12">
            <h1 className="text-4xl font-black text-[var(--color-text-primary)] mb-3">
              Observatorio de Pertinencia Educativa
            </h1>
            <p className="text-lg text-[var(--color-text-secondary)]">
              Análisis integral del programa {selectedProgram}
            </p>
          </header>

          {/* Section: Estado de Pertinencia */}
          <EstadoSection />

          {/* Section: Qué Demanda Mercado */}
          <MercadoSection />

          {/* Section: Qué Enseña Programa */}
          <ProgramaSection />

          {/* Section: Cobertura Curricular */}
          <CoberturaSection />

          {/* Section: Brechas Identificadas */}
          <BrechasSection />

          {/* Section: Empleos Compatibles */}
          <EmpleosSection />

          {/* Section: Simulación de Mejora */}
          <SimulacionSection />

          {/* Section: Recomendaciones */}
          <RecomendacionesSection />



          {/* Footer */}
          <footer className="mt-20 pt-16 pb-8 border-t border-[var(--color-border)]">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
              <div>
                <h4 className="font-bold text-[var(--color-text-primary)] mb-3">Sobre este Observatorio</h4>
                <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                  Herramienta de inteligencia curricular para UNIR Colombia que analiza pertinencia educativa y empleabilidad de programas académicos.
                </p>
              </div>
              <div>
                <h4 className="font-bold text-[var(--color-text-primary)] mb-3">Navegación Rápida</h4>
                <ul className="space-y-2 text-sm">
                  {navigationItems.slice(0, 4).map((item) => (
                    <li key={item.id}>
                      <button
                        onClick={() => scrollToSection(item.id)}
                        className="text-[var(--color-text-secondary)] hover:text-[var(--color-accent-red)] transition-colors"
                      >
                        {item.label}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="font-bold text-[var(--color-text-primary)] mb-3">Información</h4>
                <p className="text-sm text-[var(--color-text-secondary)] mb-2">
                  <strong>Institución:</strong> UNIR Colombia
                </p>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  <strong>Actualizado:</strong> Junio 2024
                </p>
              </div>
            </div>

            <div className="border-t border-[var(--color-border)] pt-8 text-center">
              <p className="text-xs text-[var(--color-text-secondary)] mb-2">
                Datos en construcción • Este observatorio es una herramienta analítica actualizada regularmente
              </p>
              <p className="text-xs text-[var(--color-text-secondary)]">
                © 2024 UNIR Colombia • Inteligencia Curricular
              </p>
            </div>
          </footer>
        </div>
      </main>
    </div>
  );
}
