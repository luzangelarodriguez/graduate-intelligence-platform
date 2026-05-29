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

export interface MicroRecommendation {
  recommendation_type: string;
  title: string;
  recommendation_text: string;
  text?: string;
  confidence_score: number;
  confidence?: number;
  gap_detectado: string;
  evidencia_curricular: string;
  evidencia_laboral: string;
  asignatura_o_modulo_sugerido: string;
  accion_curricular: string;
  prioridad: string;
  justificacion: string;
  nivel_impacto: string;
  explanation: string;
  subdomain: string;
}

export interface MicroEntity {
  entity: string;
  entity_type: string;
  normalized_skill: string;
  domain: string;
  confidence: number;
  source?: string;
  text_fragment?: string;
}

export interface MicroAnalysis {
  id?: string | number;
  run_id?: string;
  document: {
    filename?: string;
    source_document?: string;
    extension?: string;
    content_hash?: string;
    extraction_method?: string;
    clean_text_chars?: number;
  };
  detected_domain: string;
  detected_subdomain: string;
  confidence: number;
  confidence_level?: string;
  detected_entities?: MicroEntity[];
  entities: MicroEntity[];
  skills: string[];
  technical_skills?: string[];
  transversal_skills: string[];
  platforms: string[];
  tools: string[];
  databases?: string[];
  cloud_providers?: string[];
  frameworks?: string[];
  methodologies: string[];
  real_market_gaps?: string[];
  strengthening_areas?: string[];
  market_gaps: string[];
  recommendations: MicroRecommendation[];
  scores: Record<string, number>;
  score_percent: Record<string, number>;
  executive_summary: {
    headline: string;
    narrative: string;
    decision_signal: string;
    top_actions: string[];
  };
}

export interface SpecializationOption {
  id: string;
  nombre: string;
  facultad?: string;
  nivel?: string;
  estado?: string;
}

export interface MicrocurriculumDocument {
  file_name: string;
  path: string;
  extension: string;
  status: string;
}

export interface SpecializationDocumentsResponse {
  specialization: string;
  documents: MicrocurriculumDocument[];
}

export interface SpecializationMicroAnalysis extends MicroAnalysis {
  specialization: string;
  documents_processed: number;
  documents?: MicroAnalysis['document'][];
}

export interface CurriculumTraceabilityRow {
  document_name: string;
  section: string;
  original_text: string;
  action: string;
  rewritten_text: string;
  reason: string;
  market_signal: string;
  confidence: number;
}

export interface RewrittenMicrocurriculumItem {
  rewrite_id: string;
  document_name: string;
  specialization: string;
  assignment: string;
  focus: string;
  file_path: string;
  download_url?: string;
  rewritten_curriculum: Record<string, string>;
  change_traceability: CurriculumTraceabilityRow[];
}

export interface SpecializationRewriteResponse {
  specialization: string;
  documents_processed: number;
  items: RewrittenMicrocurriculumItem[];
  traceability_path: string;
  traceability_download_url?: string;
  summary_path: string;
  output_dir: string;
}

export interface MicroDemoCase {
  id: string;
  document_name: string;
  expected_domain?: string;
  expected_subdomain?: string;
  detected_domain?: string;
  confidence?: number;
  score?: number;
  recommendations_count?: number;
}

// Observatory API Types

export interface ObservatoryMetric {
  metric_name: string;
  metric_value: number | string;
  metric_category?: string;
  unit?: string;
  trend?: string;
  timestamp?: string;
}

export interface HealthResponse {
  status: string;
  database: string;
  timestamp: string;
  checks?: Record<string, boolean>;
  observatory_freshness?: {
    last_update?: string;
    records_count?: number;
    status?: string;
  };
}

export interface EmergingSkill {
  skill_name: string;
  demand_count: number;
  trend?: string;
  growth_rate?: number;
  category?: string;
}

export interface CurriculumGap {
  specialization: string;
  specialization_id?: number;
  gap_skill: string;
  gap_severity: number;
  market_demand: number;
  coverage_percent?: number;
  priority?: string;
}

export interface ObservatoryRecommendation {
  recommendation_id?: string;
  recommendation_type: string;
  title: string;
  description: string;
  target_company?: string;
  target_specialization?: string;
  impact_level?: string;
  confidence?: number;
  created_at?: string;
}

export interface CompanyIntelligence {
  company_name: string;
  job_count: number;
  top_skills?: string[];
  avg_salary_range?: string;
  hiring_trend?: string;
  industry?: string;
}

export interface SemanticRole {
  role_name: string;
  role_family?: string;
  demand_count: number;
  avg_skills_required?: number;
  trend?: string;
}

export interface CareerPath {
  path_name: string;
  entry_role: string;
  target_role: string;
  required_skills?: string[];
  time_estimate?: string;
}

export interface MarketForecast {
  entity_type: string;
  entity_name: string;
  forecast_period: string;
  predicted_demand: number;
  confidence_interval?: number;
}

export interface PaginatedObservatoryResponse<T = Record<string, unknown>> {
  items: T[];
  count: number;
  limit: number;
  offset: number;
  filters?: Record<string, string | null>;
}
