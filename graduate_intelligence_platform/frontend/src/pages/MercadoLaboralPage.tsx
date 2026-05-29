import { useState } from 'react';
import {
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

type TabId = 'skills' | 'companies' | 'roles';

export function MercadoLaboralPage() {
  const { emergingSkills, companies, roles, isLoading, error, refresh } =
    useMercadoLaboral();
  const [activeTab, setActiveTab] = useState<TabId>('skills');

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

  if (error && !emergingSkills.length && !companies.length && !roles.length) {
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
  const totalRoles = roles.length;
  const totalDemand = emergingSkills.reduce((sum, s) => sum + (s.demand_count || 0), 0);

  // Prepare chart data for top skills
  const skillsChartData = emergingSkills.slice(0, 15).map((s) => ({
    label: s.skill_name,
    value: s.demand_count,
    maxValue: emergingSkills[0]?.demand_count || 100,
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="page-title">Mercado Laboral</h1>
            <p className="page-subtitle text-balance">
              Analisis de skills emergentes, empresas contratantes y roles con mayor demanda en el mercado.
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
          label="Skills Emergentes"
          value={totalSkills}
          description="Competencias identificadas"
          icon={<Wrench size={18} />}
          featured
        />
        <KpiCard
          label="Empresas Activas"
          value={totalCompanies}
          description="Con vacantes recientes"
          icon={<Building2 size={18} />}
        />
        <KpiCard
          label="Roles Demandados"
          value={totalRoles}
          description="Perfiles laborales"
          icon={<BriefcaseBusiness size={18} />}
        />
        <KpiCard
          label="Demanda Total"
          value={totalDemand.toLocaleString()}
          description="Menciones de skills"
          icon={<TrendingUp size={18} />}
        />
      </KpiGrid>

      {/* Tab Navigation */}
      <div className="tabs w-fit">
        <button
          type="button"
          className={`tab ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          Skills Emergentes
        </button>
        <button
          type="button"
          className={`tab ${activeTab === 'companies' ? 'active' : ''}`}
          onClick={() => setActiveTab('companies')}
        >
          Empresas
        </button>
        <button
          type="button"
          className={`tab ${activeTab === 'roles' ? 'active' : ''}`}
          onClick={() => setActiveTab('roles')}
        >
          Roles
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'skills' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Skills Chart */}
          <section className="exec-card p-5">
            <SectionHeader
              title="Top 15 Skills por Demanda"
              description="Competencias mas solicitadas por las empresas"
            />
            {skillsChartData.length > 0 ? (
              <HorizontalBarChart
                data={skillsChartData}
                showPercentage={false}
                formatValue={(v) => `${v}`}
              />
            ) : (
              <EmptyState
                title="Sin datos de skills"
                body="El observatorio aun no tiene datos de competencias emergentes."
              />
            )}
          </section>

          {/* Skills Table */}
          <section className="exec-card overflow-hidden">
            <div className="p-4 border-b border-line">
              <SectionHeader
                title="Detalle de Skills"
                description="Todas las competencias identificadas"
              />
            </div>
            <DataTable
              data={emergingSkills}
              keyExtractor={(s) => `${s.skill_name}-${emergingSkills.indexOf(s)}`}
              emptyMessage="Sin skills registradas"
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
          </section>
        </div>
      )}

      {activeTab === 'companies' && (
        <section className="exec-card overflow-hidden">
          <div className="p-4 border-b border-line">
            <SectionHeader
              title="Empresas con Mayor Actividad"
              description="Organizaciones con mas vacantes activas"
            />
          </div>
          {companies.length > 0 ? (
            <DataTable
              data={companies}
              keyExtractor={(c) => `${c.company_name}-${companies.indexOf(c)}`}
              emptyMessage="Sin empresas registradas"
              columns={[
                {
                  key: 'company_name',
                  header: 'Empresa',
                  render: (c) => (
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-8 h-8 rounded bg-canvas">
                        <Building2 size={14} className="text-muted" />
                      </div>
                      <span className="font-medium">{c.company_name}</span>
                    </div>
                  ),
                },
                {
                  key: 'job_count',
                  header: 'Vacantes',
                  align: 'center',
                  width: '100px',
                  render: (c) => (
                    <StatusBadge
                      status={c.job_count > 20 ? 'success' : c.job_count > 5 ? 'neutral' : 'warning'}
                      label={`${c.job_count}`}
                    />
                  ),
                },
                {
                  key: 'industry',
                  header: 'Industria',
                  render: (c) => c.industry || '-',
                },
                {
                  key: 'hiring_trend',
                  header: 'Tendencia',
                  width: '120px',
                  render: (c) =>
                    c.hiring_trend ? (
                      <StatusBadge
                        status={
                          c.hiring_trend === 'growing'
                            ? 'success'
                            : c.hiring_trend === 'declining'
                            ? 'danger'
                            : 'neutral'
                        }
                        label={c.hiring_trend}
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
                title="Sin datos de empresas"
                body="El observatorio aun no tiene inteligencia empresarial."
              />
            </div>
          )}
        </section>
      )}

      {activeTab === 'roles' && (
        <section className="exec-card overflow-hidden">
          <div className="p-4 border-b border-line">
            <SectionHeader
              title="Roles Laborales Demandados"
              description="Perfiles profesionales mas buscados"
            />
          </div>
          {roles.length > 0 ? (
            <DataTable
              data={roles}
              keyExtractor={(r) => `${r.role_name}-${roles.indexOf(r)}`}
              emptyMessage="Sin roles registrados"
              columns={[
                {
                  key: 'role_name',
                  header: 'Rol',
                  render: (r) => (
                    <span className="font-medium">{r.role_name}</span>
                  ),
                },
                {
                  key: 'role_family',
                  header: 'Familia',
                  render: (r) =>
                    r.role_family ? (
                      <StatusBadge status="accent" label={r.role_family} />
                    ) : (
                      '-'
                    ),
                },
                {
                  key: 'demand_count',
                  header: 'Demanda',
                  align: 'center',
                  width: '100px',
                  render: (r) => (
                    <span className="font-semibold">{r.demand_count}</span>
                  ),
                },
                {
                  key: 'avg_skills_required',
                  header: 'Skills Req.',
                  align: 'center',
                  width: '100px',
                  render: (r) =>
                    r.avg_skills_required ? `${r.avg_skills_required}` : '-',
                },
                {
                  key: 'trend',
                  header: 'Tendencia',
                  width: '100px',
                  render: (r) =>
                    r.trend ? (
                      <StatusBadge
                        status={
                          r.trend === 'rising'
                            ? 'success'
                            : r.trend === 'falling'
                            ? 'danger'
                            : 'neutral'
                        }
                        label={r.trend}
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
                title="Sin datos de roles"
                body="El observatorio aun no tiene informacion de roles semanticos."
              />
            </div>
          )}
        </section>
      )}
    </div>
  );
}
