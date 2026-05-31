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

export interface CurriculumRiskDriver {
  driver: string;
  value: number;
  impact: number;
  evidence: string[];
}

export interface CurriculumRiskResponse {
  program_id: number;
  program_name: string;
  risk_score: number;
  risk_level: string;
  risk_drivers: CurriculumRiskDriver[];
  recommended_actions: string[];
  supporting_evidence: Record<string, unknown>;
  source_tables: string[];
  confidence: number;
}

export interface UniversityMarketAlignmentResponse {
  program_id: number;
  program_name: string;
  alignment_score: number;
  alignment_level: string;
  current_alignment: number;
  projected_alignment_if_added: number;
  missing_skills: string[];
  emerging_skills: string[];
  company_demand_score: number;
  labor_demand_score: number;
  forecasted_demand_score: number;
  emerging_technology_score: number;
  explanation: string;
  supporting_evidence: Record<string, unknown>;
  source_tables: string[];
  confidence: number;
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
  microcurriculum_context?: Record<string, unknown> | null;
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

export interface RecommendationV2 {
  recommendation_type: string;
  target_entity: string;
  target_company: string;
  recommendation_score: number;
  priority: string;
  business_justification: string;
  expected_impact: string;
  confidence: number;
  estimated_alignment_increase: number;
  recommendation_evidence: Record<string, unknown>;
  recommendation_reasoning: string;
}

export interface ExecutiveObservatoryMetric {
  metric_name: string;
  metric_category: string;
  metric_value: number;
  metric_period: string;
  confidence_score: number;
  source_tables: string[];
  supporting_evidence: Record<string, unknown>;
}

export interface ExecutiveObservatoryResponse {
  metrics: ExecutiveObservatoryMetric[];
  alignment_average: number;
  high_risk_programs: Record<string, unknown>[];
  medium_risk_programs: Record<string, unknown>[];
  low_risk_programs: Record<string, unknown>[];
  programs_analyzed: number;
  critical_gaps: Record<string, unknown>[];
  top_emerging_skills: Record<string, unknown>[];
  top_recommendations: Record<string, unknown>[];
  top_programs: Record<string, unknown>[];
  at_risk_programs: Record<string, unknown>[];
  executive_narrative: string;
  source_tables: string[];
  confidence: number;
}

export interface ExecutiveNarrativeResponse {
  program_id?: number | null;
  program_name: string;
  narrative: string;
  why_at_risk: string;
  evidence_sources: string[];
  source_tables: string[];
  supporting_evidence: Record<string, unknown>;
  confidence: number;
  model: string;
  generated_at: string;
}

export interface ProgramSummaryResponse {
  program_id: number;
  program_name: string;
  summary: string;
  why_at_risk: string;
  microcurriculum_traceability: Record<string, unknown>;
  evidence_sources: string[];
  source_tables: string[];
  supporting_evidence: Record<string, unknown>;
  confidence: number;
  model: string;
  generated_at: string;
}

export interface RecommendationExplanationResponse {
  recommendation_id: number;
  recommendation_title: string;
  explanation: string;
  why_this_recommendation: string;
  evidence_sources: string[];
  source_tables: string[];
  supporting_evidence: Record<string, unknown>;
  confidence: number;
  model: string;
  generated_at: string;
}

export interface AskObservatoryRequest {
  question: string;
  program_id?: number | null;
  recommendation_id?: number | null;
  context?: Record<string, unknown>;
}

export interface AskObservatoryResponse {
  question: string;
  answer: string;
  evidence_sources: string[];
  source_tables: string[];
  supporting_evidence: Record<string, unknown>;
  confidence: number;
  model: string;
  generated_at: string;
}

export interface ProgramIntelligenceItem {
  program_id: number;
  program_name: string;
  program_role: string;
  alignment_score: number;
  risk_score: number;
  risk_level: string;
  gap_count: number;
  top_gaps: Record<string, unknown>[];
  top_recommendations: Record<string, unknown>[];
  forecast_signals: Record<string, unknown>[];
  role_signals: Record<string, unknown>[];
  emerging_technologies: Record<string, unknown>[];
  recommended_actions: string[];
  business_justification: string;
  supporting_evidence: Record<string, unknown>;
  source_tables: string[];
  confidence: number;
  generated_at: string;
}

export interface ProgramIntelligencePageResponse extends Page<ProgramIntelligenceItem> {
  total: number;
  filters: Record<string, unknown>;
  source_tables: string[];
  confidence: number;
}

export interface EmergingSkillSignal {
  skill_name: string;
  growth_rate: number;
  confidence_score: number;
  first_seen_date?: string | null;
  last_seen_date?: string | null;
  supporting_companies?: string[];
  supporting_roles?: string[];
  evidence?: Record<string, unknown>;
  skill?: string;
  market_weight?: number;
  market_signal_confidence?: number;
  reason?: string;
}

export interface CompanyIntelligenceItem {
  company: string;
  dominant_stack?: string;
  dominant_cluster?: string;
  hiring_velocity?: number;
  ai_adoption_score?: number;
  cloud_maturity_score?: number;
  bi_maturity_score?: number;
  technology_maturity?: string;
  top_skills?: string[];
  top_clusters?: string[];
  evidence?: Record<string, unknown>;
}

export interface MarketForecastItem {
  entity_type: string;
  entity_name: string;
  horizon_months: number;
  growth_velocity: number;
  forecast_confidence: number;
  market_phase: string;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  evidence?: Record<string, unknown>;
}

export interface CriticalProgramItem {
  program_id: number;
  program_name: string;
  program_role: string;
  alignment_score: number;
  risk_score: number;
  risk_level: string;
  gap_count: number;
  main_gap_driver: string;
  recommended_action: string;
  projected_employability_gain: number;
  horizon_months: number;
  supporting_evidence: Record<string, unknown>;
  source_tables: string[];
  confidence: number;
  generated_at: string;
}

export interface CriticalProgramPageResponse extends Page<CriticalProgramItem> {
  filters: Record<string, unknown>;
}

export interface CurriculumSimulationResponse {
  program_id: number;
  program_name: string;
  program_role: string;
  horizon_months: number;
  current_alignment_score: number;
  current_risk_score: number;
  projected_alignment_score: number;
  projected_risk_score: number;
  projected_employability_gain: number;
  projected_gap_reduction: number;
  confidence_score: number;
  proposed_skills: string[];
  normalized_skills: Record<string, unknown>[];
  risk_drivers: Record<string, unknown>[];
  supporting_evidence: Record<string, unknown>;
  source_tables: string[];
  explanation: string;
  simulation_key: string;
  generated_at: string;
}

export interface ForecastSummaryResponse {
  generated_at: string;
  source_tables: string[];
  total_records: number;
  counts: Record<string, number>;
  coverage: Record<string, number>;
  top_skills: MarketForecastItem[];
  top_technologies: MarketForecastItem[];
  top_companies: MarketForecastItem[];
  top_roles: MarketForecastItem[];
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
