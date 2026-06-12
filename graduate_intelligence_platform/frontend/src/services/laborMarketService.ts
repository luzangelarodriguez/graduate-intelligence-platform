import { getCompanyIntelligence, getEmpleos, getForecastSummary, getMarketForecast, getMatches } from './api';
import { requestResource } from './serviceState';

export const laborMarketService = {
  listJobs: () =>
    requestResource(
      '/api/empleos',
      () => getEmpleos(100),
      'No se encontraron vacantes laborales disponibles para el análisis.',
      'Revise la ejecución de crawlers, la carga Bronze/Silver, los endpoints laborales o VITE_API_BASE_URL.',
    ),
  listMatches: () =>
    requestResource(
      '/api/matches',
      () => getMatches(100),
      'No se encontraron relaciones entre programas y vacantes.',
      'Valide la normalización de skills y la generación de matches programa-vacante.',
    ),
  listCompanies: () =>
    requestResource(
      '/company-intelligence',
      () => getCompanyIntelligence(50),
      'No hay inteligencia de empresas disponible.',
      'Revise la extracción laboral y la agregación por empresa.',
    ),
  listMarketForecast: () =>
    requestResource(
      '/market-forecast',
      () => getMarketForecast(50),
      'No hay proyección laboral disponible.',
      'Valide la generación de señales temporales y entidades de mercado.',
    ),
  getForecastSummary: () =>
    requestResource(
      '/forecast-summary',
      () => getForecastSummary(50),
      'No hay resumen de proyección disponible.',
      'Revise la tabla de proyección y su agregación ejecutiva.',
    ),
};







