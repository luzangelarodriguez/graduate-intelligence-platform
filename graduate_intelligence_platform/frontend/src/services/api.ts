import axios from 'axios';

import type {
  AlumniRegistrationPayload,
  AlumniRegistrationResponse,
  AuthUser,
  CompanyIntelligenceItem,
  AskObservatoryRequest,
  AskObservatoryResponse,
  DashboardKpisResponse,
  CriticalProgramPageResponse,
  CurriculumRiskResponse,
  EmergingSkillSignal,
  Job,
  LoginPayload,
  Match,
  MicroAnalysis,
  MicroDemoCase,
  ForecastSummaryResponse,
  MarketForecastItem,
  SpecializationDocumentsResponse,
  SpecializationMicroAnalysis,
  SpecializationOption,
  SpecializationRewriteResponse,
  Page,
  Program,
  ProgramIntelligencePageResponse,
  ProgramDashboardResponse,
  RelatedUniversityProgram,
  RegisterPayload,
  RecommendationProgram,
  RecommendationV2,
  ExecutiveObservatoryResponse,
  ExecutiveNarrativeResponse,
  UniversityMarketAlignmentResponse,
  CurriculumSimulationResponse,
  ProgramSummaryResponse,
  RecommendationExplanationResponse,
  TokenPair,
} from '../types/api';

const envBaseUrl = (import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL) as string | undefined;
let accessToken = window.localStorage.getItem('gi_access_token') || '';

if (import.meta.env.DEV) {
  console.info('API Base URL:', envBaseUrl || '/');
}

export const apiClient = axios.create({
  baseURL: envBaseUrl || '',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  if ((envBaseUrl === '/api' || envBaseUrl?.endsWith('/api')) && typeof config.url === 'string' && config.url.startsWith('/api/')) {
    config.url = config.url.replace(/^\/api/, '');
  }
  return config;
});

export function setAccessToken(token: string) {
  accessToken = token;
  if (token) {
    window.localStorage.setItem('gi_access_token', token);
  } else {
    window.localStorage.removeItem('gi_access_token');
  }
}

export function getStoredRefreshToken() {
  return window.localStorage.getItem('gi_refresh_token') || '';
}

export function setRefreshToken(token: string) {
  if (token) {
    window.localStorage.setItem('gi_refresh_token', token);
  } else {
    window.localStorage.removeItem('gi_refresh_token');
  }
}

export async function login(payload: LoginPayload) {
  const { data } = await apiClient.post<TokenPair>('/auth/login', payload);
  setAccessToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

export async function registerUser(payload: RegisterPayload) {
  const { data } = await apiClient.post<TokenPair>('/auth/register', payload);
  setAccessToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

export async function refreshSession(refreshToken: string) {
  const { data } = await apiClient.post<TokenPair>('/auth/refresh', { refresh_token: refreshToken });
  setAccessToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

export async function logoutSession(refreshToken: string) {
  await apiClient.post('/auth/logout', { refresh_token: refreshToken || null });
  setAccessToken('');
  setRefreshToken('');
}

export async function getMe() {
  const { data } = await apiClient.get<AuthUser>('/auth/me');
  return data;
}

export async function getBootstrap() {
  const { data } = await apiClient.get('/api/bootstrap');
  return data;
}

export async function getDashboardKpis() {
  const { data } = await apiClient.get<DashboardKpisResponse>('/api/dashboard/kpis');
  return data;
}

export async function getExecutiveObservatory() {
  const { data } = await apiClient.get<ExecutiveObservatoryResponse>('/executive-observatory');
  return data;
}

export async function getExecutiveNarrative(programId?: number) {
  const { data } = await apiClient.get<ExecutiveNarrativeResponse>('/executive-narrative', {
    params: programId ? { program_id: programId } : undefined,
  });
  return data;
}

export async function getProgramSummary(programId: number) {
  const { data } = await apiClient.get<ProgramSummaryResponse>(`/program-summary/${programId}`);
  return data;
}

export async function getRecommendationExplanation(recommendationId: number) {
  const { data } = await apiClient.get<RecommendationExplanationResponse>(`/recommendation-explanation/${recommendationId}`);
  return data;
}

export async function askObservatory(payload: AskObservatoryRequest) {
  const { data } = await apiClient.post<AskObservatoryResponse>('/ask-observatory', payload);
  return data;
}

export async function getCurriculumRisk(programId: number) {
  const { data } = await apiClient.get<CurriculumRiskResponse>(`/programas/${programId}/curriculum-risk`);
  return data;
}

export async function getProgramAlignment(programId: number) {
  const { data } = await apiClient.get<UniversityMarketAlignmentResponse>(`/programas/${programId}/alignment`);
  return data;
}

export async function getCurriculumSimulator(programId: number, proposedSkills: string[], horizonMonths = 12) {
  const { data } = await apiClient.get<CurriculumSimulationResponse>('/curriculum-simulator', {
    params: {
      program_id: programId,
      proposed_skills: proposedSkills.join(', '),
      horizon_months: horizonMonths,
    },
  });
  return data;
}

export async function getForecastSummary(limit = 25) {
  const { data } = await apiClient.get<ForecastSummaryResponse>('/forecast-summary', {
    params: { limit },
  });
  return data;
}

export async function getCriticalPrograms(limit = 20, horizonMonths = 12) {
  const { data } = await apiClient.get<CriticalProgramPageResponse>('/critical-programs', {
    params: { limit, offset: 0, horizon_months: horizonMonths },
  });
  return data;
}

export async function getProgramDashboard(programId: number) {
  const { data } = await apiClient.get<ProgramDashboardResponse>(`/api/dashboard/programa/${programId}`);
  return data;
}

export async function getProgramas(limit = 100) {
  const { data } = await apiClient.get<Page<Program>>('/api/programas', {
    params: { limit },
  });
  return data;
}

export async function getSpecializations() {
  const { data } = await apiClient.get<SpecializationOption[]>('/api/specializations');
  return data;
}

export async function getPrograma(programId: number) {
  const { data } = await apiClient.get<Program>(`/api/programas/${programId}`);
  return data;
}

export async function getProgramIntelligence(limit = 100) {
  const { data } = await apiClient.get<ProgramIntelligencePageResponse>('/program-intelligence', {
    params: { limit, offset: 0 },
  });
  return data;
}

export async function getProgramIntelligenceDetail(programId: number) {
  const { data } = await apiClient.get<ProgramIntelligencePageResponse['items'][number]>(`/program-intelligence/${programId}`);
  return data;
}

export async function getRelatedUniversityPrograms(programId: number, limit = 10) {
  const { data } = await apiClient.get<Page<RelatedUniversityProgram>>(
    `/api/programs/related-universities/${programId}`,
    { params: { limit } },
  );
  return data;
}

export async function getEmpleos(limit = 50) {
  const { data } = await apiClient.get<Page<Job>>('/api/empleos', {
    params: { limit },
  });
  return data;
}

export async function getMatches(limit = 50) {
  const { data } = await apiClient.get<Page<Match>>('/api/matches', {
    params: { limit },
  });
  return data;
}

export async function getProgramMatches(programId: number, limit = 25) {
  const { data } = await apiClient.get<Page<Match>>(`/api/matches/programa/${programId}`, {
    params: { limit },
  });
  return data;
}

export async function getProgramRecommendations(programId: number, limit = 5) {
  const { data } = await apiClient.get<Page<RecommendationProgram>>('/api/recommendations/programs', {
    params: { program_id: programId, limit },
  });
  return data;
}

export async function getJobRecommendations(programId: number, limit = 8) {
  const { data } = await apiClient.get<Page<Match>>('/api/recommendations/jobs', {
    params: { program_id: programId, limit },
  });
  return data;
}

export async function getRecommendationsV2(programId?: number, limit = 12) {
  const { data } = await apiClient.get<Page<RecommendationV2>>('/recommendations-v2', {
    params: { program_id: programId ?? undefined, limit, offset: 0 },
  });
  return data;
}

export async function getEmergingSkills(limit = 12) {
  const { data } = await apiClient.get<Page<EmergingSkillSignal>>('/emerging-skills', {
    params: { limit, offset: 0 },
  });
  return data;
}

export async function getCompanyIntelligence(limit = 12) {
  const { data } = await apiClient.get<Page<CompanyIntelligenceItem>>('/company-intelligence', {
    params: { limit, offset: 0 },
  });
  return data;
}

export async function getMarketForecast(limit = 12) {
  const { data } = await apiClient.get<Page<MarketForecastItem>>('/market-forecast', {
    params: { limit, offset: 0 },
  });
  return data;
}

export async function registerAlumni(payload: AlumniRegistrationPayload) {
  const { data } = await apiClient.post<AlumniRegistrationResponse>('/api/alumni/register', payload);
  return data;
}

export async function analyzeMicrocurriculum(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<MicroAnalysis>('/api/microcurriculum/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
  return data;
}

export async function getMicrocurriculumDemoCases() {
  const { data } = await apiClient.get<{ items: MicroDemoCase[]; summary: Record<string, unknown> }>(
    '/api/microcurriculum/demo-cases',
  );
  return data;
}

export async function getSpecializationMicrocurriculumDocuments(specializationId: string) {
  const { data } = await apiClient.get<SpecializationDocumentsResponse>(
    `/api/microcurriculum/specialization/${encodeURIComponent(specializationId)}/documents`,
  );
  return data;
}

export async function analyzeSpecializationMicrocurriculums(specializationId: string) {
  const { data } = await apiClient.post<SpecializationMicroAnalysis>(
    `/api/microcurriculum/specialization/${encodeURIComponent(specializationId)}/analyze`,
  );
  return data;
}

export async function rewriteSpecializationMicrocurriculums(specializationId: string) {
  const { data } = await apiClient.post<SpecializationRewriteResponse>(
    `/api/microcurriculum/specialization/${encodeURIComponent(specializationId)}/rewrite`,
    {},
    { timeout: 120000 },
  );
  return data;
}

export async function getMicrocurriculumExecutiveReport(caseId: string) {
  const { data } = await apiClient.get<{ id: string; format: string; analysis?: MicroAnalysis; markdown: string }>(
    `/api/microcurriculum/${encodeURIComponent(caseId)}/executive-report`,
  );
  return data;
}
