import axios from 'axios';

import type {
  AlumniRegistrationPayload,
  AlumniRegistrationResponse,
  AuthUser,
  CareerPath,
  CompanyIntelligence,
  CurriculumGap,
  DashboardKpisResponse,
  EmergingSkill,
  HealthResponse,
  Job,
  LoginPayload,
  MarketForecast,
  Match,
  MicroAnalysis,
  MicroDemoCase,
  ObservatoryMetric,
  ObservatoryRecommendation,
  PaginatedObservatoryResponse,
  SemanticRole,
  SpecializationDocumentsResponse,
  SpecializationMicroAnalysis,
  SpecializationOption,
  SpecializationRewriteResponse,
  Page,
  Program,
  ProgramDashboardResponse,
  RelatedUniversityProgram,
  RegisterPayload,
  RecommendationProgram,
  TokenPair,
} from '../types/api';

const envBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
let accessToken = window.localStorage.getItem('gi_access_token') || '';

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

// Observatory API Endpoints

export async function getObservatoryHealth() {
  const { data } = await apiClient.get<HealthResponse>('/health');
  return data;
}

export async function getObservatoryMetrics(params?: { limit?: number; offset?: number; metric_category?: string; metric_name?: string }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<ObservatoryMetric>>('/metrics', { params });
  return data;
}

export async function getEmergingSkills(params?: { limit?: number; offset?: number }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<EmergingSkill>>('/emerging-skills', { params });
  return data;
}

export async function getCurriculumGaps(params?: { limit?: number; offset?: number; specialization?: string }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<CurriculumGap>>('/curriculum-gaps', { params });
  return data;
}

export async function getObservatoryRecommendations(params?: { limit?: number; offset?: number; recommendation_type?: string; target_company?: string }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<ObservatoryRecommendation>>('/recommendations', { params });
  return data;
}

export async function getCompanyIntelligence(params?: { limit?: number; offset?: number }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<CompanyIntelligence>>('/company-intelligence', { params });
  return data;
}

export async function getSemanticRoles(params?: { limit?: number; offset?: number; role_family?: string }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<SemanticRole>>('/semantic-roles', { params });
  return data;
}

export async function getCareerPaths(params?: { limit?: number; offset?: number }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<CareerPath>>('/career-paths', { params });
  return data;
}

export async function getMarketForecast(params?: { limit?: number; offset?: number; entity_type?: string }) {
  const { data } = await apiClient.get<PaginatedObservatoryResponse<MarketForecast>>('/market-forecast', { params });
  return data;
}

// Wrapper for programs that returns PaginatedObservatoryResponse format
export async function getPrograms(params?: { limit?: number; offset?: number }) {
  const limit = params?.limit || 100;
  const result = await getProgramas(limit);
  return {
    items: result.items,
    count: result.count,
    limit,
    offset: params?.offset || 0,
  } as PaginatedObservatoryResponse<Program>;
}
