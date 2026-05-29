import {
  BarChart3,
  BookOpen,
  BriefcaseBusiness,
  Building2,
  GraduationCap,
  Lightbulb,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';

import {
  EmptyState,
  HorizontalBarChart,
  KpiCard,
  KpiGrid,
  SectionHeader,
  SkeletonKpiGrid,
  SkeletonTable,
  StatusBadge,
} from '../components/ui';
import { useObservatoryDashboard } from '../hooks/useObservatoryDashboard';

export function DashboardPage() {
  const { metrics, emergingSkills, companies, health, isLoading, error, refresh } =
    useObservatoryDashboard();

  // Extract key metrics from the API response
  const getMetricValue = (name: string): number | string => {
    const metric = metrics.find(
      (m) => m.metric_name.toLowerCase().includes(name.toLowerCase())
    );
    return metric?.metric_value ?? 0;
  };

  const totalPrograms = getMetricValue('program') || getMetricValue('especializacion') || metrics.length;
  const totalSkills = getMetricValue('skill') || emergingSkills.length;
  const totalCompanies = getMetricValue('company') || getMetricValue('empresa') || companies.length;
  const totalRecommendations = getMetricValue('recommendation') || getMetricValue('recomendacion') || 0;
  const alignmentIndex = getMetricValue('alignment') || getMetricValue('alineacion') || 0;
  const totalJobs = getMetricValue('job') || getMetricValue('empleo') || 0;

  // Transform skills data for the chart
  const skillsChartData = emergingSkills.slice(0, 10).map((skill) => ({
    label: skill.skill_name,
    value: skill.demand_count,
    maxValue: emergingSkills[0]?.demand_count || 100,
  }));

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <div className="skeleton skeleton-title w-64 mb-2" />
          <div className="skeleton skeleton-text w-96" />
        </div>
        <SkeletonKpiGrid count={6} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonTable rows={8} />
          <SkeletonTable rows={8} />
        </div>
      </div>
    );
  }

  if (error && !metrics.length && !emergingSkills.length) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h1 className="page-title">Dashboard Ejecutivo</h1>
          <p className="page-subtitle">Observatorio curricular de UNIR Colombia</p>
        </div>
        <div className="exec-card p-6">
          <EmptyState
            title="Error de conexion"
            body={error}
            action={
              <button type="button" className="btn btn-primary" onClick={refresh}>
                <RefreshCw size={16} />
                Reintentar
              </button>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="page-title">Dashboard Ejecutivo</h1>
            <p className="page-subtitle text-balance">
              Vision integral del observatorio curricular, demanda laboral y brechas de
              habilidades para orientar decisiones academicas.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {health && (
              <StatusBadge
                status={health.status === 'ok' ? 'success' : 'warning'}
                label={health.status === 'ok' ? 'Activo' : 'Limitado'}
                dot
              />
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={refresh}
              aria-label="Actualizar datos"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* KPI Grid */}
      <KpiGrid columns={6}>
        <KpiCard
          label="Programas Analizados"
          value={totalPrograms}
          description="Especializaciones en el sistema"
          icon={<GraduationCap size={18} />}
          featured
        />
        <KpiCard
          label="Skills Identificadas"
          value={totalSkills}
          description="Competencias del mercado"
          icon={<BarChart3 size={18} />}
        />
        <KpiCard
          label="Empresas Analizadas"
          value={totalCompanies}
          description="Fuentes de demanda laboral"
          icon={<Building2 size={18} />}
        />
        <KpiCard
          label="Empleos Relacionados"
          value={totalJobs}
          description="Vacantes procesadas"
          icon={<BriefcaseBusiness size={18} />}
        />
        <KpiCard
          label="Recomendaciones"
          value={totalRecommendations}
          description="Sugerencias generadas"
          icon={<Lightbulb size={18} />}
        />
        <KpiCard
          label="Indice Alineacion"
          value={typeof alignmentIndex === 'number' ? `${alignmentIndex}%` : alignmentIndex}
          description="Promedio curricular"
          icon={<TrendingUp size={18} />}
        />
      </KpiGrid>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Skills */}
        <section className="exec-card p-5">
          <SectionHeader
            title="Skills con Mayor Demanda"
            description="Competencias mas solicitadas por el mercado laboral"
          />
          {skillsChartData.length > 0 ? (
            <HorizontalBarChart data={skillsChartData} showPercentage={false} formatValue={(v) => `${v}`} />
          ) : (
            <EmptyState
              title="Sin datos de skills"
              body="El observatorio aun no tiene datos de competencias emergentes."
            />
          )}
        </section>

        {/* Top Companies */}
        <section className="exec-card p-5">
          <SectionHeader
            title="Principales Empleadores"
            description="Empresas con mayor actividad de contratacion"
          />
          {companies.length > 0 ? (
            <div className="company-grid">
              {companies.slice(0, 9).map((company, index) => (
                <div key={`${company.company_name}-${index}`} className="company-card">
                  <p className="company-card-name truncate">{company.company_name}</p>
                  <p className="company-card-metric">
                    {company.job_count} {company.job_count === 1 ? 'vacante' : 'vacantes'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Sin datos de empresas"
              body="El observatorio aun no tiene datos de inteligencia empresarial."
            />
          )}
        </section>
      </div>

      {/* Observatory Status */}
      {health?.observatory_freshness && (
        <section className="exec-card p-5">
          <SectionHeader
            title="Estado del Observatorio"
            description="Informacion sobre la actualizacion de datos"
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-canvas rounded">
              <span className="text-xs font-semibold text-muted uppercase tracking-wide">
                Ultima actualizacion
              </span>
              <p className="text-sm font-semibold text-ink mt-1">
                {health.observatory_freshness.last_update
                  ? new Date(health.observatory_freshness.last_update).toLocaleDateString('es-CO', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })
                  : 'No disponible'}
              </p>
            </div>
            <div className="p-4 bg-canvas rounded">
              <span className="text-xs font-semibold text-muted uppercase tracking-wide">
                Registros procesados
              </span>
              <p className="text-sm font-semibold text-ink mt-1">
                {health.observatory_freshness.records_count?.toLocaleString() ?? 'N/A'}
              </p>
            </div>
            <div className="p-4 bg-canvas rounded">
              <span className="text-xs font-semibold text-muted uppercase tracking-wide">
                Estado
              </span>
              <p className="text-sm font-semibold text-ink mt-1 flex items-center gap-2">
                <span className={`status-dot ${health.observatory_freshness.status === 'fresh' ? 'online' : 'warning'}`} />
                {health.observatory_freshness.status === 'fresh' ? 'Actualizado' : 'Requiere actualizacion'}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Additional Metrics */}
      {metrics.length > 0 && (
        <section className="exec-card p-5">
          <SectionHeader
            title="Metricas del Observatorio"
            description="Indicadores detallados del sistema"
          />
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Metrica</th>
                  <th>Valor</th>
                  <th>Categoria</th>
                  <th>Tendencia</th>
                </tr>
              </thead>
              <tbody>
                {metrics.slice(0, 10).map((metric, index) => (
                  <tr key={`${metric.metric_name}-${index}`}>
                    <td className="font-medium">{metric.metric_name}</td>
                    <td>
                      {metric.metric_value}
                      {metric.unit && ` ${metric.unit}`}
                    </td>
                    <td>
                      {metric.metric_category ? (
                        <StatusBadge status="neutral" label={metric.metric_category} />
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>
                      {metric.trend ? (
                        <StatusBadge
                          status={
                            metric.trend === 'up'
                              ? 'success'
                              : metric.trend === 'down'
                              ? 'danger'
                              : 'neutral'
                          }
                          label={metric.trend}
                        />
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
