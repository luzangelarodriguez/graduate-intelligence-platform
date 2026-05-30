import {
  BarChart3,
  Building2,
  GraduationCap,
  Lightbulb,
  RefreshCw,
  Target,
  TrendingUp,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  EmptyState,
  KpiCard,
  KpiGrid,
  SectionHeader,
  SkeletonKpiGrid,
  SkeletonTable,
  StatusBadge,
} from '../components/ui';
import { useObservatoryDashboard } from '../hooks/useObservatoryDashboard';

// Color palette for charts
const COLORS = {
  primary: '#003A70',
  secondary: '#0066B3',
  accent: '#E87722',
  success: '#059669',
  warning: '#D97706',
  neutral: '#6B7280',
};

const PIE_COLORS = ['#003A70', '#0066B3', '#059669', '#D97706', '#6B7280'];

export function DashboardPage() {
  const { programs, companies, recommendations, gaps, kpis, health, isLoading, error, refresh } =
    useObservatoryDashboard();

  // Prepare data for charts
  const topProgramsByMatch = [...programs]
    .sort((a, b) => (b.promedio_match_mercado || 0) - (a.promedio_match_mercado || 0))
    .slice(0, 8)
    .map((p) => ({
      name: p.nombre_especializacion.replace('Especializacion en ', '').slice(0, 25),
      match: Math.round(p.promedio_match_mercado || 0),
      empleos: p.total_empleos_relacionados || 0,
    }));

  const companiesByHiring = [...companies]
    .sort((a, b) => parseFloat(b.hiring_velocity) - parseFloat(a.hiring_velocity))
    .slice(0, 6)
    .map((c) => ({
      name: c.company.slice(0, 20),
      contratacion: Math.round(parseFloat(c.hiring_velocity) * 100),
      ia: Math.round(parseFloat(c.ai_adoption_score) * 100),
    }));

  const gapsBySeverity = gaps.reduce((acc, gap) => {
    const severity = gap.gap_severity >= 70 ? 'Alta' : gap.gap_severity >= 40 ? 'Media' : 'Baja';
    acc[severity] = (acc[severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const gapsPieData = Object.entries(gapsBySeverity).map(([name, value]) => ({ name, value }));

  const recommendationsByType = recommendations.reduce((acc, rec) => {
    const type = rec.recommendation_type || 'otro';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const recsPieData = Object.entries(recommendationsByType).map(([name, value]) => ({ name, value }));

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

  if (error && !programs.length && !companies.length) {
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
                label={health.status === 'ok' ? 'Conectado' : 'Limitado'}
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

      {/* KPI Grid - Clean numbers, no decimals */}
      <KpiGrid columns={6}>
        <KpiCard
          label="Programas"
          value={kpis.totalPrograms}
          description="Especializaciones activas"
          icon={<GraduationCap size={18} />}
          featured
        />
        <KpiCard
          label="Empresas"
          value={kpis.totalCompanies}
          description="Fuentes de demanda"
          icon={<Building2 size={18} />}
        />
        <KpiCard
          label="Recomendaciones"
          value={kpis.totalRecommendations}
          description="Sugerencias IA"
          icon={<Lightbulb size={18} />}
        />
        <KpiCard
          label="Brechas"
          value={kpis.totalGaps}
          description="Skills faltantes"
          icon={<Target size={18} />}
        />
        <KpiCard
          label="Match Promedio"
          value={`${Math.round(kpis.avgMatchMercado)}%`}
          description="Alineacion curricular"
          icon={<TrendingUp size={18} />}
        />
        <KpiCard
          label="Adopcion IA"
          value={`${Math.round(kpis.avgAiAdoption * 100)}%`}
          description="Promedio empresas"
          icon={<BarChart3 size={18} />}
        />
      </KpiGrid>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Programs by Match */}
        <section className="exec-card p-5">
          <SectionHeader
            title="Programas por Alineacion"
            description="Top especializaciones con mayor match al mercado"
          />
          {topProgramsByMatch.length > 0 ? (
            <div className="h-72 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topProgramsByMatch} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    width={140} 
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                  />
                  <Tooltip 
                    formatter={(value: number) => [`${value}%`, 'Match']}
                    contentStyle={{ fontSize: 12, borderRadius: 6 }}
                  />
                  <Bar dataKey="match" fill={COLORS.primary} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sin datos" body="No hay programas registrados." />
          )}
        </section>

        {/* Companies by Hiring */}
        <section className="exec-card p-5">
          <SectionHeader
            title="Empresas por Contratacion"
            description="Velocidad de contratacion vs adopcion IA"
          />
          {companiesByHiring.length > 0 ? (
            <div className="h-72 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={companiesByHiring} margin={{ left: 0, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={60} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip 
                    formatter={(value: number, name: string) => [
                      `${value}%`, 
                      name === 'contratacion' ? 'Contratacion' : 'Adopcion IA'
                    ]}
                    contentStyle={{ fontSize: 12, borderRadius: 6 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="contratacion" name="Contratacion" fill={COLORS.primary} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="ia" name="Adopcion IA" fill={COLORS.accent} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sin datos" body="No hay empresas registradas." />
          )}
        </section>
      </div>

      {/* Charts Row 2 - Pie Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gaps by Severity */}
        <section className="exec-card p-5">
          <SectionHeader
            title="Brechas por Severidad"
            description="Distribucion de brechas curriculares"
          />
          {gapsPieData.length > 0 ? (
            <div className="h-64 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={gapsPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                    labelLine={false}
                  >
                    {gapsPieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [value, 'Brechas']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sin brechas" body="No hay brechas curriculares identificadas." />
          )}
        </section>

        {/* Recommendations by Type */}
        <section className="exec-card p-5">
          <SectionHeader
            title="Recomendaciones por Tipo"
            description="Clasificacion de sugerencias IA"
          />
          {recsPieData.length > 0 ? (
            <div className="h-64 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={recsPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                    labelLine={false}
                  >
                    {recsPieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [value, 'Recomendaciones']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sin recomendaciones" body="No hay recomendaciones generadas." />
          )}
        </section>
      </div>

      {/* Top Companies Table */}
      {companies.length > 0 && (
        <section className="exec-card p-5">
          <SectionHeader
            title="Inteligencia Empresarial"
            description="Indicadores de madurez tecnologica por empresa"
          />
          <div className="overflow-x-auto mt-4">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Empresa</th>
                  <th className="text-center">Contratacion</th>
                  <th className="text-center">Adopcion IA</th>
                  <th className="text-center">Cloud</th>
                  <th className="text-center">BI</th>
                  <th>Stack Dominante</th>
                </tr>
              </thead>
              <tbody>
                {companies.slice(0, 8).map((company, index) => (
                  <tr key={`${company.company}-${index}`}>
                    <td className="font-medium">{company.company}</td>
                    <td className="text-center">
                      <span className="font-semibold text-primary">
                        {Math.round(parseFloat(company.hiring_velocity) * 100)}%
                      </span>
                    </td>
                    <td className="text-center">
                      {Math.round(parseFloat(company.ai_adoption_score) * 100)}%
                    </td>
                    <td className="text-center">
                      {Math.round(parseFloat(company.cloud_maturity_score) * 100)}%
                    </td>
                    <td className="text-center">
                      {Math.round(parseFloat(company.bi_maturity_score) * 100)}%
                    </td>
                    <td>
                      <StatusBadge status="neutral" label={company.dominant_stack || '-'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Observatory Status */}
      {health?.observatory_freshness && (
        <section className="exec-card p-5">
          <SectionHeader
            title="Estado del Sistema"
            description="Informacion sobre la actualizacion de datos"
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
            <div className="p-4 bg-canvas rounded-lg">
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
            <div className="p-4 bg-canvas rounded-lg">
              <span className="text-xs font-semibold text-muted uppercase tracking-wide">
                Registros procesados
              </span>
              <p className="text-sm font-semibold text-ink mt-1">
                {health.observatory_freshness.records_count?.toLocaleString() ?? 'N/A'}
              </p>
            </div>
            <div className="p-4 bg-canvas rounded-lg">
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
    </div>
  );
}
