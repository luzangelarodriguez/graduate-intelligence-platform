import {
  BarChart3,
  BookOpenCheck,
  BriefcaseBusiness,
  ClipboardCheck,
  DatabaseZap,
  GraduationCap,
  Landmark,
  Lightbulb,
  LayoutDashboard,
  Settings,
  SlidersHorizontal,
} from 'lucide-react';

export const institutionalNavigation = [
  {
    to: '/',
    label: 'Inicio ejecutivo',
    description: 'Resumen institucional para directivos académicos.',
    icon: BarChart3,
  },
  {
    to: '/dashboard-v1',
    label: 'Dashboard v1',
    description: 'Vista visible de pertinencia académica y mercado.',
    icon: LayoutDashboard,
  },
  {
    to: '/diagnostico',
    label: 'Diagnóstico institucional',
    description: 'Estado de alineación, riesgo y brechas por programa.',
    icon: ClipboardCheck,
  },
  {
    to: '/programas',
    label: 'Programas académicos',
    description: 'Detalle de inteligencia curricular por programa.',
    icon: GraduationCap,
  },
  {
    to: '/mercado-laboral',
    label: 'Mercado laboral',
    description: 'Vacantes, roles, empresas, fuentes y skills demandadas.',
    icon: BriefcaseBusiness,
  },
  {
    to: '/skills-brechas',
    label: 'Skills y brechas',
    description: 'Cobertura curricular, demanda y prioridades de intervención.',
    icon: BookOpenCheck,
  },
  {
    to: '/snies',
    label: 'Universidades / SNIES',
    description: 'Benchmark académico y universidades comparables.',
    icon: Landmark,
  },
  {
    to: '/simulacion',
    label: 'Simulación curricular',
    description: 'Impacto proyectado al fortalecer skills priorizadas.',
    icon: SlidersHorizontal,
  },
  {
    to: '/recomendaciones',
    label: 'Recomendaciones',
    description: 'Acciones priorizadas con evidencia y confianza.',
    icon: Lightbulb,
  },
  {
    to: '/calidad-datos',
    label: 'Evidencia y calidad de datos',
    description: 'Conexión, endpoints, vacíos y acciones técnicas.',
    icon: DatabaseZap,
  },
  {
    to: '/configuracion',
    label: 'Configuración',
    description: 'Parámetros de despliegue y conexión del frontend.',
    icon: Settings,
  },
] as const;



