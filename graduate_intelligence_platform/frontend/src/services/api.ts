import axios from 'axios';

import type {
  AlumniRegistrationPayload,
  AlumniRegistrationResponse,
  AuthUser,
  DashboardKpisResponse,
  Job,
  LoginPayload,
  Match,
  Page,
  Program,
  ProgramDashboardResponse,
  RelatedUniversityProgram,
  RegisterPayload,
  RecommendationProgram,
  SourceGovernanceRow,
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

export async function getSourceGovernanceDashboard() {
  const response = await fetch(`/source_governance_dashboard.json?ts=${Date.now()}`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error('No fue posible cargar la gobernanza de fuentes.');
  }
  return (await response.json()) as SourceGovernanceRow[];
}
