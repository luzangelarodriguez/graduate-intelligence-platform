import { useState, useMemo } from 'react';
import {
  BookOpen,
  ChevronRight,
  GraduationCap,
  Search,
  Target,
  TrendingUp,
  Wrench,
} from 'lucide-react';

import {
  DataTable,
  Drawer,
  EmptyState,
  HorizontalBarChart,
  KpiCard,
  KpiGrid,
  ProgressBar,
  SectionHeader,
  SkeletonKpiGrid,
  SkeletonTable,
  StatusBadge,
} from '../components/ui';
import { useOfertaAcademica } from '../hooks/useOfertaAcademica';

export function OfertaAcademicaPage() {
  const {
    programs,
    selectedProgram,
    programDashboard,
    selectedProgramId,
    setSelectedProgramId,
    isLoading,
    isProgramLoading,
    error,
  } = useOfertaAcademica();

  const [searchQuery, setSearchQuery] = useState('');
  const [showDetail, setShowDetail] = useState(false);

  const filteredPrograms = useMemo(() => {
    if (!searchQuery.trim()) return programs;
    const query = searchQuery.toLowerCase();
    return programs.filter(
      (p) =>
        p.nombre_especializacion.toLowerCase().includes(query) ||
        p.rol?.toLowerCase().includes(query)
    );
  }, [programs, searchQuery]);

  const skillsChartData = useMemo(() => {
    const skills = selectedProgram?.skills ?? programDashboard?.missing_skills ?? [];
    return skills.slice(0, 8).map((s) => ({
      label: s.nombre,
      value: s.conteo ?? 1,
      maxValue: Math.max(...skills.map((sk) => sk.conteo ?? 1), 1),
    }));
  }, [selectedProgram, programDashboard]);

  const handleSelectProgram = (programId: number) => {
    setSelectedProgramId(programId);
    setShowDetail(true);
  };

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

  if (error && !programs.length) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h1 className="page-title">Oferta Academica</h1>
          <p className="page-subtitle">Catalogo de programas academicos de UNIR Colombia</p>
        </div>
        <div className="exec-card p-6">
          <EmptyState title="Error de conexion" body={error} />
        </div>
      </div>
    );
  }

  const totalPrograms = programs.length;
  const avgMatch = programs.reduce((sum, p) => sum + (p.promedio_match_mercado || 0), 0) / (totalPrograms || 1);
  const totalSkills = programs.reduce((sum, p) => sum + (p.total_skills_programa || 0), 0);
  const totalJobs = programs.reduce((sum, p) => sum + (p.total_empleos_relacionados || 0), 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Oferta Academica</h1>
        <p className="page-subtitle text-balance">
          Catalogo de especializaciones con analisis de cobertura curricular y pertinencia laboral.
        </p>
      </div>

      {/* KPI Grid */}
      <KpiGrid columns={4}>
        <KpiCard
          label="Total Programas"
          value={totalPrograms}
          description="Especializaciones activas"
          icon={<GraduationCap size={18} />}
          featured
        />
        <KpiCard
          label="Match Promedio"
          value={`${avgMatch.toFixed(1)}%`}
          description="Alineacion con mercado"
          icon={<Target size={18} />}
        />
        <KpiCard
          label="Skills Totales"
          value={totalSkills}
          description="En todos los programas"
          icon={<Wrench size={18} />}
        />
        <KpiCard
          label="Empleos Relacionados"
          value={totalJobs}
          description="Vacantes identificadas"
          icon={<TrendingUp size={18} />}
        />
      </KpiGrid>

      {/* Search and Filter */}
      <div className="filter-bar">
        <div className="filter-item flex-1 max-w-md">
          <label>Buscar programa</label>
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
            />
            <input
              type="text"
              className="form-input pl-9"
              placeholder="Nombre o rol..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Programs Table */}
      <section className="exec-card overflow-hidden">
        <div className="p-4 border-b border-line">
          <SectionHeader
            title="Programas Academicos"
            description={`${filteredPrograms.length} programas encontrados`}
          />
        </div>
        <DataTable
          data={filteredPrograms}
          keyExtractor={(p) => p.especializacion_id}
          onRowClick={(p) => handleSelectProgram(p.especializacion_id)}
          emptyMessage="No se encontraron programas con esos criterios"
          columns={[
            {
              key: 'nombre_especializacion',
              header: 'Programa',
              render: (p) => (
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-8 h-8 rounded bg-accent-light">
                    <BookOpen size={14} className="text-accent" />
                  </div>
                  <div>
                    <p className="font-semibold text-ink">{p.nombre_especializacion}</p>
                    {p.rol && <p className="text-xs text-muted">{p.rol}</p>}
                  </div>
                </div>
              ),
            },
            {
              key: 'total_skills_programa',
              header: 'Skills',
              align: 'center',
              width: '100px',
              render: (p) => (
                <span className="font-semibold">{p.total_skills_programa || 0}</span>
              ),
            },
            {
              key: 'promedio_match_mercado',
              header: 'Match Mercado',
              width: '180px',
              render: (p) => (
                <div className="flex items-center gap-3">
                  <ProgressBar
                    value={p.promedio_match_mercado || 0}
                    variant={
                      (p.promedio_match_mercado || 0) >= 70
                        ? 'success'
                        : (p.promedio_match_mercado || 0) >= 40
                        ? 'warning'
                        : 'danger'
                    }
                  />
                  <span className="text-xs font-semibold text-muted w-10 text-right">
                    {(p.promedio_match_mercado || 0).toFixed(0)}%
                  </span>
                </div>
              ),
            },
            {
              key: 'total_empleos_relacionados',
              header: 'Empleos',
              align: 'center',
              width: '100px',
              render: (p) => (
                <StatusBadge
                  status={
                    (p.total_empleos_relacionados || 0) > 50
                      ? 'success'
                      : (p.total_empleos_relacionados || 0) > 10
                      ? 'neutral'
                      : 'warning'
                  }
                  label={`${p.total_empleos_relacionados || 0}`}
                />
              ),
            },
            {
              key: 'actions',
              header: '',
              width: '50px',
              render: () => (
                <ChevronRight size={16} className="text-muted" />
              ),
            },
          ]}
        />
      </section>

      {/* Program Detail Drawer */}
      <Drawer
        open={showDetail}
        onClose={() => setShowDetail(false)}
        title={selectedProgram?.nombre_especializacion || 'Detalle del programa'}
        subtitle={selectedProgram?.rol}
      >
        {isProgramLoading ? (
          <div className="space-y-4">
            <SkeletonKpiGrid count={3} />
          </div>
        ) : selectedProgram ? (
          <div className="space-y-6">
            {/* Program KPIs */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-canvas rounded">
                <span className="text-xs font-semibold text-muted uppercase">Match Mercado</span>
                <p className="text-xl font-bold text-ink mt-1">
                  {(selectedProgram.promedio_match_mercado || 0).toFixed(1)}%
                </p>
              </div>
              <div className="p-3 bg-canvas rounded">
                <span className="text-xs font-semibold text-muted uppercase">Skills Programa</span>
                <p className="text-xl font-bold text-ink mt-1">
                  {selectedProgram.total_skills_programa || 0}
                </p>
              </div>
              <div className="p-3 bg-canvas rounded">
                <span className="text-xs font-semibold text-muted uppercase">Herramientas</span>
                <p className="text-xl font-bold text-ink mt-1">
                  {selectedProgram.total_herramientas || 0}
                </p>
              </div>
              <div className="p-3 bg-canvas rounded">
                <span className="text-xs font-semibold text-muted uppercase">Empleos</span>
                <p className="text-xl font-bold text-ink mt-1">
                  {selectedProgram.total_empleos_relacionados || 0}
                </p>
              </div>
            </div>

            {/* Skills Distribution */}
            {skillsChartData.length > 0 && (
              <div>
                <h4 className="text-sm font-bold text-ink mb-3">Skills del Programa</h4>
                <HorizontalBarChart
                  data={skillsChartData}
                  showPercentage={false}
                  formatValue={(v) => `${v}`}
                />
              </div>
            )}

            {/* Program Dashboard Insights */}
            {programDashboard?.insights && (
              <div className="p-4 bg-accent-light rounded border border-accent/20">
                <h4 className="text-sm font-bold text-accent mb-2">Insight del Observatorio</h4>
                <p className="text-sm text-ink-light">
                  {programDashboard.insights.detected || 'Sin insights disponibles para este programa.'}
                </p>
              </div>
            )}

            {/* Missing Skills */}
            {programDashboard?.missing_skills && programDashboard.missing_skills.length > 0 && (
              <div>
                <h4 className="text-sm font-bold text-ink mb-3">Skills Faltantes</h4>
                <div className="flex flex-wrap gap-2">
                  {programDashboard.missing_skills.slice(0, 12).map((skill, i) => (
                    <span
                      key={`${skill.nombre}-${i}`}
                      className="badge badge-warning"
                    >
                      {skill.nombre}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            title="Programa no encontrado"
            body="No se pudo cargar la informacion del programa seleccionado."
          />
        )}
      </Drawer>
    </div>
  );
}
