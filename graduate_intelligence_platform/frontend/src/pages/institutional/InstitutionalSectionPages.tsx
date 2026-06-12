import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  DataTable,
  EmptyDiagnostic,
  LoadingPanel,
  MetricCard,
  PageHero,
  SectionCard,
  StatusBadge,
} from '../../components/institutional/InstitutionalPrimitives';
import { getApiBaseUrlLabel } from '../../config/api';
import { useInstitutionalSnapshot } from '../../hooks/useInstitutionalSnapshot';
import { average, asRecord, numberLabel, pct, priorityLabel, programEvidence, recordList, skillName, text } from './institutionalData';

function SimpleBarChart({ data, dataKey = 'valor' }: { data: Array<Record<string, unknown>>; dataKey?: string }) {
  if (!data.length) {
    return (
      <EmptyDiagnostic
        title="No hay datos disponibles para esta visualización."
        cause="El endpoint consultado respondió sin registros suficientes."
        endpoint="Endpoint asociado a la sección"
        action="Revise la carga de datos y vuelva a consultar la sección."
      />
    );
  }

  return (
    <div className="institutional-chart">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 20, top: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis dataKey="nombre" type="category" width={150} />
          <Tooltip />
          <Bar dataKey={dataKey} fill="#005EB8" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function InstitutionalDiagnosisPage() {
  const snapshot = useInstitutionalSnapshot();
  if (snapshot.isLoading) return <LoadingPanel label="Cargando diagnóstico institucional..." />;
  const highRisk = snapshot.programIntelligence.filter((program) => Number(program.risk_score || 0) >= 50);
  const chartData = snapshot.programIntelligence.slice(0, 12).map((program) => ({
    nombre: program.program_name.replace(/^Especialización en\s+/i, ''),
    valor: Number(program.risk_score || 0),
  }));

  return (
    <section className="institutional-page">
      <PageHero
        eyebrow="Diagnóstico institucional"
        title="Estado actual de alineación, riesgo y pertinencia"
        subtitle="Esta pantalla responde qué programas requieren intervención y qué evidencia sostiene la decisión."
      />
      <div className="institutional-grid four">
        <MetricCard label="Programas con inteligencia" value={numberLabel(snapshot.programIntelligence.length)} detail="Registros disponibles en program-intelligence." />
        <MetricCard label="Riesgo promedio" value={pct(average(snapshot.programIntelligence.map((program) => Number(program.risk_score || 0))))} detail="Riesgo curricular observado." />
        <MetricCard label="Programas en riesgo" value={numberLabel(highRisk.length)} detail="Programas con riesgo igual o superior al 50%." />
        <MetricCard label="Confianza promedio" value={pct(average(snapshot.programIntelligence.map((program) => Number(program.confidence || 0) * 100)))} detail="Nivel de confianza de las evidencias." />
      </div>
      <SectionCard title="Ranking de riesgo curricular" subtitle="Barras ordenadas para identificar dónde actuar primero.">
        <SimpleBarChart data={chartData} />
        <div className="institutional-conclusion">
          Conclusión: los programas con mayor riesgo deben revisarse con enfoque en brechas activas, evidencia laboral y trazabilidad curricular antes de aprobar cambios de plan de estudios.
        </div>
      </SectionCard>
    </section>
  );
}

export function LaborMarketPage() {
  const snapshot = useInstitutionalSnapshot();
  if (snapshot.isLoading) return <LoadingPanel label="Cargando mercado laboral..." />;
  const roleRows = snapshot.marketForecast.filter((item) => item.entity_type === 'role').slice(0, 10);
  const skillRows = snapshot.marketForecast.filter((item) => item.entity_type === 'skill').slice(0, 10);

  return (
    <section className="institutional-page">
      <PageHero
        eyebrow="Mercado laboral"
        title="Demanda laboral, roles y skills observadas"
        subtitle="Lectura para entender qué exige el mercado y qué evidencia laboral respalda las decisiones curriculares."
      />
      <div className="institutional-grid four">
        <MetricCard label="Vacantes recolectadas" value={numberLabel(snapshot.jobs.length)} detail="Registros entregados por /api/empleos." />
        <MetricCard label="Vacantes relacionadas" value={numberLabel(snapshot.matches.length)} detail="Matches programa-vacante disponibles." />
        <MetricCard label="Empresas detectadas" value={numberLabel(snapshot.companies.length)} detail="Empresas agregadas por inteligencia laboral." />
        <MetricCard label="Señales de proyección" value={numberLabel(snapshot.marketForecast.length)} detail="Roles, skills y entidades con proyección." />
      </div>
      <div className="institutional-grid two">
        <SectionCard title="Ranking de roles" subtitle="Roles laborales más visibles en las señales procesadas.">
          <SimpleBarChart data={roleRows.map((item) => ({ nombre: item.entity_name, valor: Number(item.growth_velocity || 0) * 100 }))} />
        </SectionCard>
        <SectionCard title="Ranking de skills demandadas" subtitle="Skills con mayor velocidad de crecimiento observada.">
          <SimpleBarChart data={skillRows.map((item) => ({ nombre: item.entity_name, valor: Number(item.growth_velocity || 0) * 100 }))} />
        </SectionCard>
      </div>
      <DataTable
        title="Vacantes relevantes"
        subtitle="Tabla laboral disponible desde el endpoint de empleos."
        columns={['Título', 'Ubicación', 'Fuente', 'Diagnóstico']}
        rows={snapshot.jobs.slice(0, 20).map((job) => [
          job.titulo,
          job.ubicacion || 'No disponible',
          'api/empleos',
          'Vacante disponible para análisis laboral. Valide relación con programas mediante matches.',
        ])}
        empty={
          <EmptyDiagnostic
            title="No se encontraron vacantes laborales disponibles para el análisis."
            cause="El endpoint laboral no entregó registros."
            endpoint="/api/empleos"
            action="Revise la ejecución de crawlers, la carga Bronze/Silver, los endpoints laborales o la variable VITE_API_BASE_URL."
          />
        }
      />
    </section>
  );
}

export function SkillsGapsPage() {
  const snapshot = useInstitutionalSnapshot();
  if (snapshot.isLoading) return <LoadingPanel label="Cargando skills y brechas..." />;
  const gaps = snapshot.programIntelligence.flatMap((program) =>
    programEvidence(program).gaps.map((gap) => ({ program: program.program_name, gap })),
  );
  const distribution = [
    { name: 'Cubiertas', value: gaps.filter(({ gap }) => text(asRecord(gap.evidence).coverage_status).toLowerCase().includes('covered')).length },
    { name: 'Parciales', value: gaps.filter(({ gap }) => text(asRecord(gap.evidence).coverage_status).toLowerCase().includes('partial')).length },
    { name: 'Ausentes', value: gaps.filter(({ gap }) => text(asRecord(gap.evidence).coverage_status).toLowerCase().includes('missing')).length },
    { name: 'Emergentes', value: snapshot.emergingSkills.length },
  ];

  return (
    <section className="institutional-page">
      <PageHero eyebrow="Skills y brechas" title="Cobertura curricular frente a demanda laboral" subtitle="Identifica skills cubiertas, parciales, ausentes y emergentes para priorizar intervención académica." />
      <div className="institutional-grid two">
        <SectionCard title="Distribución de cobertura de skills" subtitle="Estados detectados desde brechas y skills emergentes.">
          <div className="institutional-chart">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={distribution} dataKey="value" nameKey="name" outerRadius={95} label>
                  {distribution.map((row, index) => (
                    <Cell key={row.name} fill={['#2f7d68', '#b77816', '#b4232a', '#38a9dc'][index]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>
        <SectionCard title="Ranking de brechas críticas" subtitle="Prioridad combinada por urgencia, demanda y cobertura.">
          <SimpleBarChart data={gaps.slice(0, 10).map(({ gap }) => ({ nombre: skillName(gap), valor: Number(gap.urgency_score || 0) * 100 }))} />
        </SectionCard>
      </div>
      <DataTable
        title="Matriz de brechas de skills"
        subtitle="Filas directivas para decidir intervención curricular."
        columns={['Programa', 'Skill', 'Cobertura curricular', 'Demanda laboral', 'Estado', 'Prioridad', 'Fuente']}
        rows={gaps.map(({ program, gap }) => {
          const evidence = asRecord(gap.evidence);
          return [
            program,
            skillName(gap),
            pct(gap.curriculum_coverage_score),
            pct(gap.market_demand_score),
            text(evidence.coverage_status, 'Sin clasificar'),
            priorityLabel(gap.urgency_score),
            text(evidence.source, 'curriculum_gap_observatory'),
          ];
        })}
        empty={
          <EmptyDiagnostic
            title="No hay brechas de skills disponibles."
            cause="No se encontraron gaps en program-intelligence."
            endpoint="/program-intelligence"
            action="Valide microcurrículos procesados, normalización de skills y observatorio de brechas."
          />
        }
      />
    </section>
  );
}

export function SniesBenchmarkPage() {
  const snapshot = useInstitutionalSnapshot();
  if (snapshot.isLoading) return <LoadingPanel label="Cargando benchmark SNIES..." />;
  const rows = snapshot.programIntelligence.flatMap((program) => {
    const { benchmark } = programEvidence(program);
    return recordList(benchmark.benchmark_institutions).map((institution) => ({ program, institution, benchmark }));
  });

  return (
    <section className="institutional-page">
      <PageHero eyebrow="Universidades / SNIES" title="Benchmark académico y universidades comparables" subtitle="Comparación institucional para leer similitud, modalidad, dominio y señales relevantes." />
      <DataTable
        title="Benchmark SNIES / universidades"
        subtitle="Datos provenientes de evidencia embebida o endpoints de universidades relacionadas."
        columns={['Programa UNIR', 'Universidad', 'Programa comparable', 'Modalidad', 'Nivel', 'Dominio', 'Similitud', 'Señales relevantes']}
        rows={rows.map(({ program, institution, benchmark }) => [
          program.program_name,
          text(institution.institution),
          text(institution.program),
          text(institution.modality ?? institution.modalidad, 'No disponible'),
          text(institution.level ?? institution.nivel, 'No disponible'),
          text(benchmark.domain_label, 'No disponible'),
          institution.similarity_score == null ? 'No disponible' : pct(institution.similarity_score),
          text(institution.source, 'SNIES / Benchmark'),
        ])}
        empty={
          <EmptyDiagnostic
            title="No hay universidades comparables disponibles para este programa."
            cause="No se encontraron instituciones comparables en la evidencia actual."
            endpoint="/api/programs/related-universities/{programId} o /program-intelligence/{programId}"
            action="Verifique la carga SNIES, la homologación del programa, el dominio académico o el endpoint de benchmark."
          />
        }
      />
    </section>
  );
}

export function CurriculumSimulationOverviewPage() {
  const snapshot = useInstitutionalSnapshot();
  if (snapshot.isLoading) return <LoadingPanel label="Cargando simulación curricular..." />;
  const rows = snapshot.programIntelligence.slice(0, 12).map((program) => ({
    nombre: program.program_name.replace(/^Especialización en\s+/i, ''),
    valor: Math.max(0, 100 - Number(program.risk_score || 0)),
  }));

  return (
    <section className="institutional-page">
      <PageHero eyebrow="Simulación curricular" title="Impacto esperado al fortalecer skills" subtitle="Vista institucional para responder qué mejora en alineación, riesgo y empleabilidad al intervenir brechas priorizadas." />
      <SectionCard title="Mapa programa vs mercado" subtitle="Comparación inicial de empleabilidad estimada por programa. El detalle ejecuta simulación 6/12/24 meses.">
        <SimpleBarChart data={rows} />
        <div className="institutional-conclusion">
          Conclusión: use el detalle de cada programa para simular skills específicas y validar reducción de riesgo antes de aprobar cambios curriculares.
        </div>
      </SectionCard>
      <DataTable
        title="Programas listos para simulación"
        columns={['Programa', 'Alineación actual', 'Riesgo actual', 'Brechas', 'Acción']}
        rows={snapshot.programIntelligence.map((program) => [
          program.program_name,
          pct(program.alignment_score),
          pct(program.risk_score),
          numberLabel(program.gap_count),
          'Abrir detalle del programa y simular skills priorizadas en horizontes 6, 12 y 24 meses.',
        ])}
        empty={
          <EmptyDiagnostic
            title="No hay programas disponibles para simulación."
            cause="No existe inteligencia curricular con skills priorizadas."
            endpoint="/program-intelligence y /curriculum-simulator"
            action="Procese microcurrículos y valide gaps antes de ejecutar simulaciones."
          />
        }
      />
    </section>
  );
}

export function RecommendationsPage() {
  const snapshot = useInstitutionalSnapshot();
  if (snapshot.isLoading) return <LoadingPanel label="Cargando recomendaciones..." />;
  const embedded = snapshot.programIntelligence.flatMap((program) =>
    program.top_recommendations.map((recommendation) => ({ program: program.program_name, recommendation })),
  );

  return (
    <section className="institutional-page">
      <PageHero eyebrow="Recomendaciones" title="Acciones priorizadas para decisión curricular" subtitle="Cada recomendación debe diferenciar acción, evidencia, impacto, confianza y datos faltantes." />
      <DataTable
        title="Recomendaciones priorizadas"
        columns={['Tipo', 'Programa', 'Acción concreta', 'Skill o área', 'Justificación académica', 'Evidencia laboral', 'Impacto esperado', 'Confianza', 'Fuente']}
        rows={embedded.map(({ program, recommendation }) => [
          text(recommendation.recommendation_type, 'Curricular'),
          program,
          text(recommendation.recommendation_reasoning ?? recommendation.recommendation, 'Recomendación preliminar: falta texto de acción.'),
          text(recommendation.target_entity ?? recommendation.target_role ?? recommendation.missing_skill, 'Área no especificada'),
          text(recommendation.academic_rationale ?? recommendation.recommendation_reasoning, 'Justificación académica preliminar.'),
          text(recommendation.labor_evidence ?? recommendation.business_justification, 'La recomendación no tiene evidencia laboral suficiente; debe marcarse como preliminar.'),
          text(recommendation.expected_impact ?? recommendation.estimated_alignment_increase, 'Impacto no cuantificado.'),
          pct(Number(recommendation.recommendation_confidence ?? recommendation.confidence ?? 0) * 100),
          'program-intelligence.top_recommendations',
        ])}
        empty={
          <EmptyDiagnostic
            title="No hay recomendaciones priorizadas."
            cause="No se encontraron recomendaciones con evidencia suficiente."
            endpoint="/recommendations-v2 o /program-intelligence"
            action="Valide brechas, evidencia laboral y reglas de recomendación antes de presentarlas como acciones prioritarias."
          />
        }
      />
    </section>
  );
}

export function DataQualityPage() {
  const snapshot = useInstitutionalSnapshot();
  if (snapshot.isLoading) return <LoadingPanel label="Cargando evidencia y calidad de datos..." />;

  return (
    <section className="institutional-page">
      <PageHero eyebrow="Evidencia y calidad de datos" title="Trazabilidad técnica de datos y endpoints" subtitle="Pantalla obligatoria para no ocultar problemas de conexión, registros vacíos o endpoints con error." />
      <div className="institutional-grid four">
        <MetricCard label="URL base usada" value={snapshot.baseUrl ? 'Configurada' : 'No configurada'} detail={snapshot.baseUrl || getApiBaseUrlLabel()} />
        <MetricCard label="Endpoints exitosos" value={numberLabel(snapshot.qualityRows.filter((row) => row.status === 'success').length)} detail="Consultas con datos disponibles." />
        <MetricCard label="Endpoints vacíos" value={numberLabel(snapshot.qualityRows.filter((row) => row.status === 'empty').length)} detail="Consultas sin registros." />
        <MetricCard label="Endpoints con error" value={numberLabel(snapshot.qualityRows.filter((row) => row.status === 'error').length)} detail="Consultas que requieren revisión técnica." />
      </div>
      <DataTable
        title="Estado de entidades y endpoints"
        columns={['Entidad', 'Endpoint', 'Estado', 'Registros', 'Impacto', 'Acción recomendada']}
        rows={snapshot.qualityRows.map((row) => [
          row.entity,
          row.endpoint,
          <StatusBadge status={row.status} />,
          numberLabel(row.records),
          row.impact,
          row.error ? `${row.action} Error: ${row.error}` : row.action,
        ])}
        empty={
          <EmptyDiagnostic
            title="No hay snapshot de calidad."
            cause="No se pudo consultar la capa de servicios."
            endpoint="dataQualityService"
            action="Revise VITE_API_BASE_URL y conectividad con Railway."
          />
        }
      />
    </section>
  );
}

export function ConfigurationPage() {
  return (
    <section className="institutional-page">
      <PageHero eyebrow="Configuración" title="Configuración de despliegue frontend" subtitle="Parámetros requeridos para operar esta aplicación React/Vite en Vercel." />
      <DataTable
        title="Variables y despliegue"
        columns={['Elemento', 'Valor esperado', 'Impacto', 'Acción']}
        rows={[
          ['Root Directory', 'graduate_intelligence_platform/frontend', 'Vercel debe construir desde la subcarpeta del frontend.', 'Configurar Root Directory en el proyecto Vercel.'],
          ['Install Command', 'npm install', 'Instala dependencias según package-lock.json.', 'Usar npm install.'],
          ['Build Command', 'npm run build', 'Genera producción Vite.', 'No usar vite preview en producción.'],
          ['Output Directory', 'dist', 'Carpeta estática publicada por Vercel.', 'Configurar dist.'],
          ['VITE_API_BASE_URL', 'URL pública del backend Railway', 'Conecta el frontend con datos reales.', 'Configurar en Production, Preview y Development en Vercel.'],
        ]}
        empty={<span />}
      />
    </section>
  );
}







