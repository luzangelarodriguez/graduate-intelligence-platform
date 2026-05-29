import { useState } from 'react';
import {
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  RefreshCw,
  TrendingUp,
  Wrench,
} from 'lucide-react';

import {
  DataTable,
  EmptyState,
  HorizontalBarChart,
  KpiCard,
  KpiGrid,
  SectionHeader,
  SkeletonKpiGrid,
  SkeletonTable,
  StatusBadge,
} from '../components/ui';
import { useMercadoLaboral } from '../hooks/useMercadoLaboral';

type TabId = 'companies' | 'careers' | 'skills';

export function MercadoLaboralPage() {
  const { emergingSkills, companies, careerPaths, isLoading, error, refresh } =
    useMercadoLaboral();
  const [activeTab, setActiveTab] = useState<TabId>('companies');

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

  if (error && !emergingSkills.length && !companies.length && !careerPaths.length) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h1 className="page-title">Mercado Laboral</h1>
          <p className="page-subtitle">Inteligencia de demanda laboral y tendencias</p>
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

  const totalSkills = emergingSkills.length;
  const totalCompanies = companies.length;
  const totalCareerPaths = careerPaths.length;
  
  // Calculate average scores from companies
  const avgAiAdoption = companies.length > 0 
    ? (companies.reduce((sum, c) => sum + parseFloat(c.ai_adoption_score || '0'), 0) / companies.length * 100).toFixed(1)
    : '0';

  // Prepare chart data for top companies by hiring velocity
  const companiesChartData = [...companies]
    .sort((a, b) => parseFloat(b.hiring_velocity) - parseFloat(a.hiring_velocity))
    .slice(0, 10)
    .map((c) => ({
      label: c.company,
      value: parseFloat(c.hiring_velocity) * 100,
      maxValue: 100,
    }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="page-title">Mercado Laboral</h1>
            <p className="page-subtitle text-balance">
              Analisis de empresas contratantes, rutas de carrera y tendencias del mercado laboral colombiano.
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
          label="Empresas Analizadas"
          value={totalCompanies}
          description="Con inteligencia de mercado"
          icon={<Building2 size={18} />}
          featured
        />
        <KpiCard
          label="Rutas de Carrera"
          value={totalCareerPaths}
          description="Trayectorias profesionales"
          icon={<BriefcaseBusiness size={18} />}
        />
        <KpiCard
          label="Skills Emergentes"
          value={totalSkills}
          description="Competencias identificadas"
          icon={<Wrench size={18} />}
        />
        <KpiCard
          label="Adopcion IA Promedio"
          value={`${avgAiAdoption}%`}
          description="En empresas analizadas"
          icon={<TrendingUp size={18} />}
        />
      </KpiGrid>

      {/* Tab Navigation */}
      <div className="tabs w-fit">
        <button
          type="button"
          className={`tab ${activeTab === 'companies' ? 'active' : ''}`}
          onClick={() => setActiveTab('companies')}
        >
          Empresas ({totalCompanies})
        </button>
        <button
          type="button"
          className={`tab ${activeTab === 'careers' ? 'active' : ''}`}
          onClick={() => setActiveTab('careers')}
        >
          Rutas de Carrera ({totalCareerPaths})
        </button>
        <button
          type="button"
          className={`tab ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          Skills Emergentes ({totalSkills})
        </button>
      </div>

      {/* Tab Content: Companies */}
      {activeTab === 'companies' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Companies Chart */}
          <section className="exec-card p-5 lg:col-span-1">
            <SectionHeader
              title="Top Empresas"
              description="Por velocidad de contratacion"
            />
            {companiesChartData.length > 0 ? (
              <HorizontalBarChart
                data={companiesChartData}
                showPercentage
                formatValue={(v) => `${v.toFixed(0)}%`}
              />
            ) : (
              <EmptyState
                title="Sin datos"
                body="El observatorio aun no tiene datos de empresas."
              />
            )}
          </section>

          {/* Companies Table */}
          <section className="exec-card overflow-hidden lg:col-span-2">
            <div className="p-4 border-b border-line">
              <SectionHeader
                title="Inteligencia Empresarial"
                description="Madurez tecnologica y stack dominante"
              />
            </div>
            {companies.length > 0 ? (
              <DataTable
                data={companies}
                keyExtractor={(c) => `${c.company}-${companies.indexOf(c)}`}
                emptyMessage="Sin empresas registradas"
                columns={[
                  {
                    key: 'company',
                    header: 'Empresa',
                    render: (c) => (
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-8 h-8 rounded bg-canvas">
                          <Building2 size={14} className="text-muted" />
                        </div>
                        <div>
                          <span className="font-medium block">{c.company}</span>
                          <span className="text-xs text-muted">{c.dominant_cluster}</span>
                        </div>
                      </div>
                    ),
                  },
                  {
                    key: 'hiring_velocity',
                    header: 'Contratacion',
                    align: 'center',
                    width: '100px',
                    render: (c) => (
                      <StatusBadge
                        status={parseFloat(c.hiring_velocity) >= 0.7 ? 'success' : parseFloat(c.hiring_velocity) >= 0.4 ? 'warning' : 'neutral'}
                        label={`${(parseFloat(c.hiring_velocity) * 100).toFixed(0)}%`}
                      />
                    ),
                  },
                  {
                    key: 'ai_adoption_score',
                    header: 'IA',
                    align: 'center',
                    width: '80px',
                    render: (c) => `${(parseFloat(c.ai_adoption_score) * 100).toFixed(0)}%`,
                  },
                  {
                    key: 'cloud_maturity_score',
                    header: 'Cloud',
                    align: 'center',
                    width: '80px',
                    render: (c) => `${(parseFloat(c.cloud_maturity_score) * 100).toFixed(0)}%`,
                  },
                  {
                    key: 'bi_maturity_score',
                    header: 'BI',
                    align: 'center',
                    width: '80px',
                    render: (c) => `${(parseFloat(c.bi_maturity_score) * 100).toFixed(0)}%`,
                  },
                  {
                    key: 'technology_maturity',
                    header: 'Madurez',
                    width: '100px',
                    render: (c) => (
                      <StatusBadge
                        status={c.technology_maturity === 'mature' ? 'success' : c.technology_maturity === 'growing' ? 'warning' : 'neutral'}
                        label={c.technology_maturity}
                      />
                    ),
                  },
                ]}
              />
            ) : (
              <div className="p-6">
                <EmptyState
                  title="Sin datos de empresas"
                  body="El observatorio aun no tiene inteligencia empresarial."
                />
              </div>
            )}
          </section>
        </div>
      )}

      {/* Tab Content: Career Paths */}
      {activeTab === 'careers' && (
        <section className="exec-card overflow-hidden">
          <div className="p-4 border-b border-line">
            <SectionHeader
              title="Rutas de Progresion Profesional"
              description="Trayectorias de carrera identificadas en el mercado"
            />
          </div>
          {careerPaths.length > 0 ? (
            <DataTable
              data={careerPaths}
              keyExtractor={(cp) => `${cp.source_role}-${cp.target_role}-${careerPaths.indexOf(cp)}`}
              emptyMessage="Sin rutas de carrera registradas"
              columns={[
                {
                  key: 'source_role',
                  header: 'Rol Actual',
                  render: (cp) => (
                    <span className="font-medium">{cp.source_role}</span>
                  ),
                },
                {
                  key: 'arrow',
                  header: '',
                  width: '40px',
                  align: 'center',
                  render: () => (
                    <ArrowRight size={16} className="text-primary" />
                  ),
                },
                {
                  key: 'target_role',
                  header: 'Rol Objetivo',
                  render: (cp) => (
                    <span className="font-medium text-primary">{cp.target_role}</span>
                  ),
                },
                {
                  key: 'probability',
                  header: 'Probabilidad',
                  align: 'center',
                  width: '120px',
                  render: (cp) => (
                    <StatusBadge
                      status={parseFloat(cp.role_progression_probability) >= 0.7 ? 'success' : 'warning'}
                      label={`${(parseFloat(cp.role_progression_probability) * 100).toFixed(0)}%`}
                    />
                  ),
                },
                {
                  key: 'skill_gaps',
                  header: 'Skills Necesarias',
                  render: (cp) => (
                    <div className="flex flex-wrap gap-1">
                      {cp.transition_skill_gaps.slice(0, 4).map((skill) => (
                        <span key={skill} className="badge badge-neutral text-xs">
                          {skill}
                        </span>
                      ))}
                      {cp.transition_skill_gaps.length > 4 && (
                        <span className="badge badge-neutral text-xs">
                          +{cp.transition_skill_gaps.length - 4}
                        </span>
                      )}
                    </div>
                  ),
                },
              ]}
            />
          ) : (
            <div className="p-6">
              <EmptyState
                title="Sin rutas de carrera"
                body="El observatorio aun no tiene datos de progresion profesional."
              />
            </div>
          )}
        </section>
      )}

      {/* Tab Content: Skills */}
      {activeTab === 'skills' && (
        <section className="exec-card overflow-hidden">
          <div className="p-4 border-b border-line">
            <SectionHeader
              title="Skills Emergentes"
              description="Competencias con demanda creciente en el mercado"
            />
          </div>
          {emergingSkills.length > 0 ? (
            <DataTable
              data={emergingSkills}
              keyExtractor={(s) => `${s.skill_name}-${emergingSkills.indexOf(s)}`}
              emptyMessage="Sin skills emergentes"
              columns={[
                {
                  key: 'skill_name',
                  header: 'Skill',
                  render: (s) => (
                    <span className="font-medium">{s.skill_name}</span>
                  ),
                },
                {
                  key: 'demand_count',
                  header: 'Demanda',
                  align: 'right',
                  width: '100px',
                  render: (s) => (
                    <span className="font-semibold">{s.demand_count}</span>
                  ),
                },
                {
                  key: 'category',
                  header: 'Categoria',
                  render: (s) => s.category || '-',
                },
                {
                  key: 'trend',
                  header: 'Tendencia',
                  width: '100px',
                  render: (s) =>
                    s.trend ? (
                      <StatusBadge
                        status={
                          s.trend === 'rising'
                            ? 'success'
                            : s.trend === 'falling'
                            ? 'danger'
                            : 'neutral'
                        }
                        label={s.trend}
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
                title="Sin skills emergentes"
                body="El observatorio aun no tiene datos de competencias emergentes. Esto se actualizara automaticamente cuando haya nuevas tendencias."
              />
            </div>
          )}
        </section>
      )}
    </div>
  );
}
