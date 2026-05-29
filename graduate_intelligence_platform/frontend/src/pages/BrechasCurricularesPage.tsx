import { useMemo } from 'react';
import {
  AlertTriangle,
  GitCompare,
  RefreshCw,
  Target,
  TrendingDown,
} from 'lucide-react';

import {
  DataTable,
  EmptyState,
  KpiCard,
  KpiGrid,
  ProgressBar,
  SectionHeader,
  SkeletonKpiGrid,
  SkeletonTable,
  StatusBadge,
} from '../components/ui';
import { useBrechasCurriculares } from '../hooks/useBrechasCurriculares';

export function BrechasCurricularesPage() {
  const {
    gaps,
    programs,
    selectedSpecialization,
    setSelectedSpecialization,
    isLoading,
    error,
    refresh,
  } = useBrechasCurriculares();

  // Group gaps by specialization
  const gapsBySpecialization = useMemo(() => {
    const grouped: Record<string, { gaps: typeof gaps; totalSeverity: number }> = {};
    gaps.forEach((gap) => {
      const key = gap.specialization || 'Sin programa';
      if (!grouped[key]) {
        grouped[key] = { gaps: [], totalSeverity: 0 };
      }
      grouped[key].gaps.push(gap);
      grouped[key].totalSeverity += gap.gap_severity || 0;
    });
    return grouped;
  }, [gaps]);

  // Calculate summary metrics
  const totalGaps = gaps.length;
  const uniquePrograms = Object.keys(gapsBySpecialization).length;
  const avgSeverity = totalGaps > 0 
    ? gaps.reduce((sum, g) => sum + (g.gap_severity || 0), 0) / totalGaps 
    : 0;
  const criticalGaps = gaps.filter((g) => (g.gap_severity || 0) >= 0.7).length;

  // Programs with highest gap severity
  const programsRanked = useMemo(() => {
    return Object.entries(gapsBySpecialization)
      .map(([name, data]) => ({
        name,
        gapCount: data.gaps.length,
        avgSeverity: data.totalSeverity / data.gaps.length,
      }))
      .sort((a, b) => b.avgSeverity - a.avgSeverity);
  }, [gapsBySpecialization]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <div className="skeleton skeleton-title w-64 mb-2" />
          <div className="skeleton skeleton-text w-96" />
        </div>
        <SkeletonKpiGrid count={4} />
        <SkeletonTable rows={10} />
      </div>
    );
  }

  if (error && !gaps.length) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h1 className="page-title">Brechas Curriculares</h1>
          <p className="page-subtitle">Analisis de gaps entre curriculo y mercado</p>
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
            <h1 className="page-title">Brechas Curriculares</h1>
            <p className="page-subtitle text-balance">
              Identificacion de gaps entre las competencias curriculares y la demanda del mercado laboral.
            </p>
          </div>
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

      {/* KPI Grid */}
      <KpiGrid columns={4}>
        <KpiCard
          label="Brechas Identificadas"
          value={totalGaps}
          description="Skills faltantes totales"
          icon={<GitCompare size={18} />}
          featured
        />
        <KpiCard
          label="Programas Afectados"
          value={uniquePrograms}
          description="Con al menos una brecha"
          icon={<Target size={18} />}
        />
        <KpiCard
          label="Severidad Promedio"
          value={`${(avgSeverity * 100).toFixed(0)}%`}
          description="Impacto en empleabilidad"
          icon={<TrendingDown size={18} />}
        />
        <KpiCard
          label="Brechas Criticas"
          value={criticalGaps}
          description="Severidad mayor al 70%"
          icon={<AlertTriangle size={18} />}
        />
      </KpiGrid>

      {/* Filter by Program */}
      <div className="filter-bar">
        <div className="filter-item">
          <label>Filtrar por programa</label>
          <select
            className="form-select max-w-xs"
            value={selectedSpecialization || ''}
            onChange={(e) => setSelectedSpecialization(e.target.value || null)}
          >
            <option value="">Todos los programas</option>
            {programs.map((p) => (
              <option key={p.especializacion_id} value={p.nombre_especializacion}>
                {p.nombre_especializacion}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Programs Ranking */}
        <section className="exec-card p-5">
          <SectionHeader
            title="Programas por Severidad"
            description="Ordenados por impacto de brechas"
          />
          {programsRanked.length > 0 ? (
            <div className="space-y-3">
              {programsRanked.slice(0, 10).map((prog, index) => (
                <button
                  key={prog.name}
                  type="button"
                  className={`w-full text-left p-3 rounded border transition ${
                    selectedSpecialization === prog.name
                      ? 'border-accent bg-accent-light'
                      : 'border-line hover:border-muted-light'
                  }`}
                  onClick={() =>
                    setSelectedSpecialization(
                      selectedSpecialization === prog.name ? null : prog.name
                    )
                  }
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-ink truncate pr-2">
                      {index + 1}. {prog.name}
                    </span>
                    <StatusBadge
                      status={
                        prog.avgSeverity >= 0.7
                          ? 'danger'
                          : prog.avgSeverity >= 0.4
                          ? 'warning'
                          : 'success'
                      }
                      label={`${(prog.avgSeverity * 100).toFixed(0)}%`}
                    />
                  </div>
                  <ProgressBar
                    value={prog.avgSeverity * 100}
                    variant={
                      prog.avgSeverity >= 0.7
                        ? 'danger'
                        : prog.avgSeverity >= 0.4
                        ? 'warning'
                        : 'success'
                    }
                  />
                  <p className="text-xs text-muted mt-1">
                    {prog.gapCount} {prog.gapCount === 1 ? 'brecha' : 'brechas'}
                  </p>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Sin datos de programas"
              body="No hay programas con brechas identificadas."
            />
          )}
        </section>

        {/* Gaps Table */}
        <section className="exec-card overflow-hidden lg:col-span-2">
          <div className="p-4 border-b border-line">
            <SectionHeader
              title="Detalle de Brechas"
              description={
                selectedSpecialization
                  ? `Filtrado por: ${selectedSpecialization}`
                  : 'Todas las brechas identificadas'
              }
            />
          </div>
          {gaps.length > 0 ? (
            <DataTable
              data={gaps}
              keyExtractor={(g, i) => `${g.specialization}-${g.gap_skill}-${i}`}
              emptyMessage="No hay brechas que mostrar"
              columns={[
                {
                  key: 'gap_skill',
                  header: 'Skill Faltante',
                  render: (g) => (
                    <span className="font-medium">{g.gap_skill}</span>
                  ),
                },
                {
                  key: 'specialization',
                  header: 'Programa',
                  render: (g) => (
                    <span className="text-sm truncate max-w-[200px] block">
                      {g.specialization || '-'}
                    </span>
                  ),
                },
                {
                  key: 'gap_severity',
                  header: 'Severidad',
                  width: '120px',
                  render: (g) => (
                    <div className="flex items-center gap-2">
                      <ProgressBar
                        value={(g.gap_severity || 0) * 100}
                        variant={
                          (g.gap_severity || 0) >= 0.7
                            ? 'danger'
                            : (g.gap_severity || 0) >= 0.4
                            ? 'warning'
                            : 'success'
                        }
                      />
                      <span className="text-xs font-semibold text-muted w-8">
                        {((g.gap_severity || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  ),
                },
                {
                  key: 'market_demand',
                  header: 'Demanda',
                  align: 'center',
                  width: '100px',
                  render: (g) => (
                    <span className="font-semibold">
                      {g.market_demand || 0}
                    </span>
                  ),
                },
                {
                  key: 'priority',
                  header: 'Prioridad',
                  width: '100px',
                  render: (g) =>
                    g.priority ? (
                      <StatusBadge
                        status={
                          g.priority === 'alta' || g.priority === 'high'
                            ? 'danger'
                            : g.priority === 'media' || g.priority === 'medium'
                            ? 'warning'
                            : 'neutral'
                        }
                        label={g.priority}
                      />
                    ) : (
                      '-'
                    ),
                },
              ]}
            />
          ) : (
            <div className="p-6">
              <EmptyState
                title="Sin brechas identificadas"
                body="El observatorio aun no ha detectado brechas curriculares."
              />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
