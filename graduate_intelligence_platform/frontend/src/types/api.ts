export interface Page<T> {
  items: T[];
  count: number;
  limit: number;
  offset: number;
}

export interface DashboardKpis {
  total_programas: number;
  total_skills_programa: number;
  total_skills_mercado: number;
  total_empleos: number;
  total_empleos_relacionados: number;
  promedio_global_match: number;
  mejor_match_global: number;
}

export interface DashboardKpisResponse {
  kpis: DashboardKpis;
  source: string;
}

export type SourceTier = 'Gold' | 'Silver' | 'Bronze' | 'Experimental';

export interface SourceGovernanceRow {
  source: string;
  source_tier: SourceTier;
  reliability_score: number;
  freshness_score: number;
  freshness_label: string;
  contamination_rate: number;
  blocked_auth_rate: number;
  semantic_density: number;
  evidence_quality: number;
  extraction_completeness: number;
  source_stability: number;
  access_strategy: 'API' | 'scraping' | 'partnership' | 'licensed' | 'blocked_auth' | string;
  access_risk_level: 'low' | 'medium' | 'high' | string;
  gold_readiness: boolean;
  raw_runs: number;
  raw_jobs: number;
  silver_jobs: number;
  gold_jobs: number;
  notes: string;
}

export interface ProgramDashboardKpis {
  alignment_score: number;
  missing_critical_skills: number;
  high_demand_roles: number;
  employability_trend: number;
  digital_coverage: number;
  curricular_update_signal: string;
}

export interface ProgramDashboardStatus {
  curricular_status: string;
  curricular_status_detail: string;
  ai_signal: string;
  trend_label: string;
}

export interface ProgramDashboardInsights {
  detected: string;
  ai_recommends: string[];
  emerging_gap: string;
  critical_signal: string;
}

export interface ProgramDashboardResponse {
  program_id: number;
  program: Program;
  kpis: ProgramDashboardKpis;
  status: ProgramDashboardStatus;
  missing_skills: Skill[];
  matches: Match[];
  recommendations: RecommendationProgram[];
  insights: ProgramDashboardInsights;
  source: string;
}

export interface RelatedUniversityProgram {
  competidor?: string;
  universidad: string;
  programa: string;
  ciudad: string;
  nivel: string;
  modalidad: string;
  estado_programa: string;
  duracion?: string;
  creditos?: number;
  similitud: number;
}

export interface Program {
  especializacion_id: number;
  nombre_especializacion: string;
  rol: string;
  total_skills_programa: number;
  total_herramientas: number;
  total_competencias: number;
  total_habilidades_blandas: number;
  promedio_match_mercado: number;
  porcentaje_match?: number;
  max_match_mercado: number;
  total_empleos_relacionados: number;
  skills_cubiertas?: number;
  skills?: Skill[];
}

export interface Skill {
  skill_id: number;
  nombre: string;
  conteo?: number;
}

export interface Match {
  especializacion_id?: number;
  empleo_id: string;
  titulo_empleo: string;
  total_skills_empleo: number;
  total_skills_especializacion: number;
  skills_en_comun: number;
  porcentaje_match: number;
}

export interface Job {
  empleo_id: string;
  titulo: string;
  ubicacion: string;
}

export interface RecommendationProgram {
  nombre: string;
  match: number;
  reason: string;
}

export interface AlumniRegistrationPayload {
  nombre_completo: string;
  email: string;
  especializacion_id: number;
  anio_graduacion: string;
  cargo_actual: string;
  area_actual: string;
  nivel_experiencia: string;
  anios_experiencia: string;
  skills_actuales: string;
  herramientas_dia_dia: string;
  roles_interes: string;
  areas_interes: string;
  objetivo_laboral: string;
  disponibilidad: string;
}

export interface AlumniRegistrationResponse {
  id: number;
  status: string;
  message: string;
}

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  roles: string[];
  active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  full_name: string;
  role: 'admin' | 'universidad' | 'egresado' | 'mentor';
}
