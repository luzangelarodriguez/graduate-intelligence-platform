import { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  BriefcaseBusiness,
  Building2,
  CheckCircle2,
  FileText,
  GraduationCap,
  Landmark,
  LayoutDashboard,
  LineChart,
  Network,
  PenLine,
  Scale,
  ShieldCheck,
} from 'lucide-react';

import {
  committeeRows,
  employabilityMap,
  institutionalRows,
  internalRanking,
  laborRoles,
  marketTrend,
  navItems,
  programSignals,
  riskSignals,
  skillsHeatmap,
  sniesPrograms,
  technologyCoverage,
  vacancyEvidence,
} from '../data/institutional_observatory';
import {
  analyzeSpecializationMicrocurriculums,
  getRelatedUniversityPrograms,
  getSpecializationMicrocurriculumDocuments,
  getSpecializations,
  rewriteSpecializationMicrocurriculums,
} from '../services/api';
import type {
  MicrocurriculumDocument,
  RelatedUniversityProgram,
  SpecializationMicroAnalysis,
  SpecializationOption,
  SpecializationRewriteResponse,
} from '../types/api';
import {
  AuditNote,
  DataTable,
  DecisionBar,
  DocumentPanel,
  ExecutiveCard,
  MetricHero,
  ProgressRow,
  StatusMark,
} from '../components/enterprise/ObservatoryPrimitives';

type ViewId = (typeof navItems)[number];

type ObservatoryDataState = 'loading' | 'live' | 'partial' | 'demo';

type ObservatoryContext = {
  analysis: SpecializationMicroAnalysis | null;
  documents: MicrocurriculumDocument[];
  relatedPrograms: RelatedUniversityProgram[];
  selectedSpecialization: SpecializationOption | null;
  rewriteResult: SpecializationRewriteResponse | null;
  rewriting: boolean;
  dataState: ObservatoryDataState;
  message: string;
  refresh: () => Promise<void>;
  rewrite: () => Promise<void>;
};

const viewIcons: Record<ViewId, typeof LayoutDashboard> = {
  'Home ejecutivo': LayoutDashboard,
  Especializacion: GraduationCap,
  'Benchmarking SNIES': Landmark,
  Empleabilidad: BriefcaseBusiness,
  'Reescritura IA': PenLine,
  'Comite academico': Scale,
  'Detalle microcurricular': FileText,
  'Dashboard institucional': BarChart3,
};

function PageTitle({ title, body, action }: { title: string; body: string; action?: string }) {
  return (
    <header className="oi-view-title">
      <div>
        <h1>{title}</h1>
        <p>{body}</p>
      </div>
      {action ? (
        <button className="oi-primary-action" type="button">
          {action}
        </button>
      ) : null}
    </header>
  );
}

function normalizeText(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function percent(value?: number) {
  return `${Math.max(0, Math.min(100, Math.round(value ?? 0)))}%`;
}

function levelFromScore(value?: number) {
  const score = Math.max(0, Math.min(100, Math.round(value ?? 0)));
  if (score >= 93) return 'level-94' as const;
  if (score >= 89) return 'level-91' as const;
  if (score >= 84) return 'level-86' as const;
  if (score >= 79) return 'level-82' as const;
  if (score >= 74) return 'level-76' as const;
  if (score >= 70) return 'level-72' as const;
  if (score >= 65) return 'level-68' as const;
  if (score >= 59) return 'level-62' as const;
  if (score >= 52) return 'level-55' as const;
  if (score >= 43) return 'level-48' as const;
  return 'level-38' as const;
}

function uniq(items: Array<string | undefined | null>) {
  return Array.from(new Set(items.map((item) => String(item || '').trim()).filter(Boolean)));
}

function realTechnologyCoverage(analysis: SpecializationMicroAnalysis | null) {
  if (!analysis) return technologyCoverage;
  const scores = analysis.score_percent || {};
  return [
    {
      label: 'Pertinencia curricular',
      value: percent(scores.pertinencia_curricular),
      level: levelFromScore(scores.pertinencia_curricular),
      tone: 'green' as const,
    },
    {
      label: 'Cobertura mercado',
      value: percent(scores.cobertura_skills_mercado),
      level: levelFromScore(scores.cobertura_skills_mercado),
      tone: 'blue' as const,
    },
    {
      label: 'Modernizacion tecnologica',
      value: percent(scores.modernizacion_tecnologica),
      level: levelFromScore(scores.modernizacion_tecnologica),
      tone: Number(scores.modernizacion_tecnologica || 0) >= 60 ? ('blue' as const) : ('amber' as const),
    },
    {
      label: 'Riesgo obsolescencia',
      value: percent(scores.riesgo_obsolescencia),
      level: levelFromScore(scores.riesgo_obsolescencia),
      tone: Number(scores.riesgo_obsolescencia || 0) >= 60 ? ('red' as const) : ('amber' as const),
    },
  ];
}

function realSkillsHeatmap(analysis: SpecializationMicroAnalysis | null) {
  const values = uniq([
    ...(analysis?.tools || []),
    ...(analysis?.platforms || []),
    ...(analysis?.databases || []),
    ...(analysis?.cloud_providers || []),
    ...(analysis?.frameworks || []),
    ...(analysis?.technical_skills || []),
  ]).slice(0, 6);
  if (!values.length) return skillsHeatmap;
  return values.map((label, index) => ({ label, level: Math.max(3, 5 - Math.floor(index / 2)) }));
}

function realBenchmarkRows(programs: RelatedUniversityProgram[]) {
  if (!programs.length) return sniesPrograms;
  return programs.slice(0, 6).map((item, index) => [
    item.universidad || item.competidor || 'Institucion comparable',
    String(Math.round(Number(item.similitud || 0) * 100)),
    item.modalidad || 'Virtual',
    index === 0 ? 'Ref.' : `${Math.round(Number(item.similitud || 0) * 100) - 82}`,
  ]);
}

function ExecutiveHome({ analysis, documents, relatedPrograms, dataState, message }: ObservatoryContext) {
  const score = analysis?.score_percent?.pertinencia_curricular ?? 82.4;
  const realMetrics = [
    {
      label: 'Indice institucional de pertinencia',
      value: String(Math.round(score * 10) / 10),
      detail: analysis?.executive_summary?.decision_signal || 'Portafolio competitivo con presion selectiva de actualizacion.',
      tone: 'green' as const,
    },
    {
      label: 'Microcurriculos procesados',
      value: String(analysis?.documents_processed || documents.length || 0),
      detail: analysis ? 'Documentos reales analizados por el motor curricular.' : 'Pendiente de respuesta del backend.',
      tone: 'blue' as const,
    },
    {
      label: 'Universidades comparables',
      value: String(relatedPrograms.length || 24),
      detail: relatedPrograms.length ? 'Referentes reales retornados por el endpoint SNIES relacionado.' : 'Referencia demo hasta autenticar/fuente disponible.',
      tone: relatedPrograms.length ? ('green' as const) : ('blue' as const),
    },
    {
      label: 'Brechas reales detectadas',
      value: String(analysis?.real_market_gaps?.length ?? analysis?.market_gaps?.length ?? 4),
      detail: analysis ? 'Brechas consolidadas desde microcurriculos reales.' : 'Valor demo mientras carga el analisis.',
      tone: 'amber' as const,
    },
  ];
  return (
    <>
      <PageTitle
        title="Home ejecutivo"
        body="Lectura integral de salud curricular, riesgo academico, empleabilidad y posicion comparativa del portafolio institucional."
        action="Exportar informe"
      />
      <div className={`oi-source-banner oi-source-${dataState}`}>
        <ShieldCheck size={17} />
        <span>{message}</span>
      </div>
      <section className="oi-home-hero">
        <div className="oi-hero-index">
          <span>Indice institucional de pertinencia</span>
          <strong>{Math.round(score * 10) / 10}</strong>
          <p>
            {analysis?.executive_summary?.narrative ||
              'Portafolio en rango competitivo, con presion de actualizacion concentrada en analitica aplicada, gobierno de datos y evaluacion por evidencia.'}
          </p>
          <div className="oi-hero-meter">
            <i className={levelFromScore(score)} />
          </div>
        </div>
        <div className="oi-metric-stack">
          {realMetrics.slice(1).map((metric) => (
            <MetricHero key={metric.label} {...metric} />
          ))}
        </div>
      </section>
      <section className="oi-grid oi-grid-3">
        <ExecutiveCard title="Ranking interno de programas" label="Portafolio">
          <div className="oi-stack">
            {internalRanking.map((item) => (
              <ProgressRow key={item.label} item={item} />
            ))}
          </div>
        </ExecutiveCard>
        <ExecutiveCard title="Senales de riesgo curricular" label="Aseguramiento">
          <div className="oi-stack">
            {riskSignals.map((item) => (
              <ProgressRow key={item.label} item={item} />
            ))}
          </div>
        </ExecutiveCard>
        <ExecutiveCard title="Mapa de empleabilidad" label="Mercado">
          <div className="oi-stack">
            {employabilityMap.map((item) => (
              <ProgressRow key={item.label} item={item} />
            ))}
          </div>
        </ExecutiveCard>
      </section>
    </>
  );
}

function SpecializationView({ analysis, selectedSpecialization, documents }: ObservatoryContext) {
  const score = analysis?.score_percent?.pertinencia_curricular ?? 86;
  const heatmap = realSkillsHeatmap(analysis);
  const coverage = realTechnologyCoverage(analysis);
  const recommendations = analysis?.recommendations || [];
  return (
    <>
      <PageTitle
        title={selectedSpecialization?.nombre || analysis?.specialization || 'Especializacion en Visual Analytics y Big Data'}
        body={`${documents.length || analysis?.documents_processed || 0} microcurriculos disponibles para lectura curricular, empleabilidad y propuesta academica asistida.`}
        action="Cambiar programa"
      />
      <section className="oi-program-header">
        {programSignals.map((item) => (
          <article key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>
      <section className="oi-grid oi-grid-3">
        <ExecutiveCard title="Pertinencia curricular" label="Lectura principal">
          <div className="oi-gauge">
            <strong>{Math.round(score)}</strong>
            <span>/100</span>
          </div>
          <p className="oi-card-copy">
            {analysis?.executive_summary?.headline ||
              'Alta correspondencia con demanda ejecutiva, con brecha visible en automatizacion analitica aplicada.'}
          </p>
        </ExecutiveCard>
        <ExecutiveCard title="Cobertura tecnologica" label="Curriculo vs mercado">
          <div className="oi-stack">
            {coverage.map((item) => (
              <ProgressRow key={item.label} item={item} />
            ))}
          </div>
        </ExecutiveCard>
        <ExecutiveCard title="Riesgo de obsolescencia" label="Senal de actualizacion">
          <div className="oi-risk-panel">
            <StatusMark tone="amber">Prioridad media alta</StatusMark>
            <p>
              {analysis?.executive_summary?.decision_signal ||
                'El programa no requiere rediseño completo. La oportunidad esta en actualizar resultados, evidencias y tecnologias aplicadas.'}
            </p>
          </div>
        </ExecutiveCard>
      </section>
      <section className="oi-grid oi-grid-2">
        <ExecutiveCard title="Roles mas demandados" label="Inteligencia laboral">
          <DataTable headers={['Rol', 'Vacantes', 'Crecimiento']} rows={laborRoles} />
        </ExecutiveCard>
        <ExecutiveCard title="Skills y tecnologias emergentes" label="Heatmap ejecutivo">
          <div className="oi-heatmap">
            {heatmap.map((item) => (
              <div key={item.label} className={`oi-heat-cell heat-${item.level}`}>
                <strong>{item.label}</strong>
                <span>{item.level}/5</span>
              </div>
            ))}
          </div>
        </ExecutiveCard>
      </section>
      <ExecutiveCard title="Microcurriculo propuesto por IA" label="Documento academico trazable">
        <div className="oi-document-grid">
          <DocumentPanel title="Original">
            <p>Resultado de aprendizaje: construir tableros para representar indicadores de negocio.</p>
            <p>Contenido: herramientas de visualizacion, graficos basicos, preparacion de datos y publicacion.</p>
          </DocumentPanel>
          <DocumentPanel title="Actualizado" variant="proposal">
            <p>
              {recommendations[0]?.accion_curricular ||
                'Resultado de aprendizaje: diseñar tableros ejecutivos con gobierno de datos, narrativa analitica y criterios de decision institucional.'}
            </p>
            <AuditNote>
              {recommendations[0]?.justificacion ||
                'Cambio sustentado por demanda laboral en roles de analitica ejecutiva y comparacion con programas SNIES.'}
            </AuditNote>
          </DocumentPanel>
        </div>
      </ExecutiveCard>
    </>
  );
}

function BenchmarkingView({ relatedPrograms }: ObservatoryContext) {
  const rows = realBenchmarkRows(relatedPrograms);
  return (
    <>
      <PageTitle
        title="Benchmarking SNIES"
        body="Comparacion competitiva con universidades y programas equivalentes, inspirada en lectura ejecutiva tipo QS."
      />
      <section className="oi-grid oi-grid-2">
        <ExecutiveCard title="Liga competitiva de programas equivalentes" label="SNIES">
          <DataTable headers={['Universidad', 'Score', 'Cobertura', 'Gap']} rows={rows} />
        </ExecutiveCard>
        <ExecutiveCard title="Posicion competitiva" label="Cuadrante ejecutivo">
          <div className="oi-quadrant">
            <span className="q q-1">U. Andes</span>
            <span className="q q-2">UNIR</span>
            <span className="q q-3">U. Rosario</span>
            <span className="q q-4">U. Sabana</span>
          </div>
        </ExecutiveCard>
      </section>
      <section className="oi-grid oi-grid-3">
        {['Modalidad virtual internacional', 'Enfoque ejecutivo de analitica', 'Trazabilidad para comites'].map(
          (item, index) => (
            <MetricHero
              key={item}
              label="Fortaleza diferencial"
              value={`0${index + 1}`}
              detail={item}
              tone={index === 0 ? 'blue' : 'green'}
            />
          ),
        )}
      </section>
    </>
  );
}

function EmployabilityView({ analysis }: ObservatoryContext) {
  const realGaps = analysis?.real_market_gaps || analysis?.market_gaps || [];
  const rows = realGaps.length
    ? realGaps.slice(0, 4).map((gap, index) => [
        gap,
        uniq([...(analysis?.technical_skills || []), ...(analysis?.tools || [])]).slice(index, index + 3).join(', ') || 'Evidencia curricular',
        index < 2 ? 'Alta' : 'Media',
        index < 2 ? 'Actualizar resultado y evidencia' : 'Refuerzo transversal',
      ])
    : vacancyEvidence;
  return (
    <>
      <PageTitle
        title="Empleabilidad y mercado"
        body="Señales laborales traducidas a decisiones curriculares, sin convertir la plataforma en un listado operativo de vacantes."
      />
      <section className="oi-grid oi-grid-2">
        <ExecutiveCard title="Tendencia laboral relacionada" label="Mercado">
          <div className="oi-line-chart" aria-label="Tendencia de demanda laboral">
            <i />
          </div>
          <p className="oi-card-copy">
            Crecimiento sostenido en roles de analitica aplicada, con aceleracion por automatizacion y gobierno de
            datos.
          </p>
        </ExecutiveCard>
        <ExecutiveCard title="Roles de mayor demanda" label="Ranking">
          <div className="oi-stack">
            {marketTrend.map((item) => (
              <ProgressRow key={item.label} item={item} />
            ))}
          </div>
        </ExecutiveCard>
      </section>
      <ExecutiveCard title="Evidencia laboral para actualizacion curricular" label="Vinculacion academica">
        <DataTable headers={['Señal laboral', 'Competencias solicitadas', 'Prioridad', 'Implicacion curricular']} rows={rows} />
      </ExecutiveCard>
    </>
  );
}

function RewriteView({ rewriteResult, rewriting, rewrite, analysis }: ObservatoryContext) {
  const firstRewrite = rewriteResult?.items?.[0];
  const firstTrace = firstRewrite?.change_traceability?.[0];
  const firstRecommendation = analysis?.recommendations?.[0];
  return (
    <>
      <PageTitle
        title="Reescritura curricular IA"
        body="Experiencia premium para comparar microcurriculo original, propuesta institucional, diferencias, justificacion y evidencia laboral."
      />
      <button className="oi-primary-action oi-floating-action" type="button" onClick={rewrite} disabled={rewriting}>
        {rewriting ? 'Generando...' : rewriteResult ? 'Regenerar propuesta real' : 'Generar propuesta real'}
      </button>
      <section className="oi-document-grid oi-document-grid-wide">
        <DocumentPanel title="Microcurriculo original">
          <p>
            {firstTrace?.original_text ||
              'Unidad 2. Visualizacion de datos. Construir tableros de informacion para representar indicadores de negocio.'}
          </p>
          <p>Contenido: graficos basicos, preparacion de datos, publicacion de reportes y sustentacion final.</p>
        </DocumentPanel>
        <DocumentPanel title="Propuesta IA con trazabilidad institucional" variant="proposal">
          <div className="oi-diff oi-diff-add">
            <strong>Resultado actualizado</strong>
            <p>
              {firstTrace?.rewritten_text ||
                firstRecommendation?.accion_curricular ||
                'Diseñar tableros ejecutivos con gobierno de datos, narrativa analitica y criterios de decision.'}
            </p>
          </div>
          <div className="oi-diff oi-diff-change">
            <strong>Contenido enriquecido</strong>
            <p>Se incorporan metricas estrategicas, calidad de datos, Power BI avanzado y caso institucional.</p>
          </div>
          <AuditNote>
            {firstTrace?.reason ||
              firstRecommendation?.justificacion ||
              'La propuesta reduce riesgo de obsolescencia y mejora alineacion frente a universidades comparables.'}
          </AuditNote>
        </DocumentPanel>
      </section>
      {rewriteResult ? (
        <ExecutiveCard title={`${rewriteResult.documents_processed} microcurriculos generados`} label="Resultado real">
          <DataTable
            headers={['Documento', 'Asignatura', 'Foco']}
            rows={rewriteResult.items.slice(0, 5).map((item) => [item.document_name, item.assignment, item.focus])}
          />
        </ExecutiveCard>
      ) : null}
      <DecisionBar />
    </>
  );
}

function CommitteeView({ analysis }: ObservatoryContext) {
  const rows = (analysis?.recommendations || []).length
    ? analysis!.recommendations.slice(0, 4).map((item) => [
        item.asignatura_o_modulo_sugerido || item.title,
        item.prioridad === 'alta' ? 'Aprobar' : 'Actualizar',
        item.nivel_impacto || 'Medio',
        item.prioridad || 'Media',
      ])
    : committeeRows;
  return (
    <>
      <PageTitle
        title="Comite academico"
        body="Vista para decidir que aprobar, que actualizar, que retirar y cual es el impacto esperado en riesgo academico y laboral."
      />
      <section className="oi-grid oi-grid-2">
        <ExecutiveCard title="Decisiones pendientes" label="Gobierno academico">
          <DataTable headers={['Microcurriculo', 'Decision', 'Impacto', 'Riesgo']} rows={rows} />
        </ExecutiveCard>
        <ExecutiveCard title="Impacto esperado" label="Simulacion ejecutiva">
          <div className="oi-impact">
            <strong>+7.4 pts</strong>
            <p>Mejora proyectada de pertinencia institucional en el siguiente ciclo academico.</p>
          </div>
          <DecisionBar />
        </ExecutiveCard>
      </section>
    </>
  );
}

function MicroDetailView({ analysis, documents }: ObservatoryContext) {
  const docName = documents[0]?.file_name || 'Unidad: Visualizacion ejecutiva de datos';
  const recommendation = analysis?.recommendations?.[0];
  return (
    <>
      <PageTitle
        title="Detalle microcurricular"
        body="Ficha academica profunda con resultados, contenidos, evidencias, riesgos y trazabilidad de actualizacion."
      />
      <section className="oi-grid oi-grid-2">
        <DocumentPanel title={docName} variant="proposal">
          <h4>Resultados de aprendizaje</h4>
          <p>
            {recommendation?.accion_curricular ||
              'Diseñar tableros ejecutivos orientados a decisiones institucionales, aplicando criterios de calidad, gobierno y narrativa analitica.'}
          </p>
          <h4>Contenidos actualizados</h4>
          <p>Modelado de indicadores, storytelling ejecutivo, gobierno de datos y evaluacion por caso aplicado.</p>
          <h4>Trazabilidad institucional</h4>
          <p>Mercado laboral validado, comparacion SNIES ajustada y revision de comite pendiente.</p>
        </DocumentPanel>
        <ExecutiveCard title="Lectura ejecutiva" label="Ficha de riesgo">
          <div className="oi-stack">
            {technologyCoverage.map((item) => (
              <ProgressRow key={item.label} item={item} />
            ))}
          </div>
        </ExecutiveCard>
      </section>
    </>
  );
}

function InstitutionalDashboardView({ analysis, documents, relatedPrograms }: ObservatoryContext) {
  const metrics = [
    {
      label: 'Microcurriculos evaluados',
      value: String(analysis?.documents_processed || documents.length || 0),
      detail: 'Documentos reales encontrados para la especializacion activa.',
      tone: 'blue' as const,
    },
    {
      label: 'Pertinencia promedio',
      value: percent(analysis?.score_percent?.pertinencia_curricular),
      detail: analysis ? 'Score real consolidado del motor curricular.' : 'Pendiente de analisis real.',
      tone: 'green' as const,
    },
    {
      label: 'Brechas detectadas',
      value: String(analysis?.real_market_gaps?.length ?? analysis?.market_gaps?.length ?? 0),
      detail: 'Brechas reales consolidadas por evidencia curricular.',
      tone: 'amber' as const,
    },
    {
      label: 'Comparables SNIES',
      value: String(relatedPrograms.length || 0),
      detail: 'Programas relacionados retornados por el backend.',
      tone: relatedPrograms.length ? ('green' as const) : ('slate' as const),
    },
  ];
  return (
    <>
      <PageTitle
        title="Dashboard institucional"
        body="Portafolio agregado para rectoria, decanaturas, direccion academica y aseguramiento de calidad."
      />
      <section className="oi-grid oi-grid-4">
        {metrics.map((metric) => (
          <MetricHero key={metric.label} {...metric} />
        ))}
      </section>
      <section className="oi-grid oi-grid-2">
        <ExecutiveCard title="Matriz de portafolio academico" label="Facultades">
          <DataTable headers={['Facultad', 'Pert.', 'Criticos', 'Demanda']} rows={institutionalRows} />
        </ExecutiveCard>
        <ExecutiveCard title="Roadmap de actualizacion" label="Ciclo academico">
          <div className="oi-roadmap">
            {['Mayo: comite posgrados', 'Junio: ajuste microcurriculos', 'Julio: validacion empleadores', 'Agosto: publicacion academica', 'Septiembre: seguimiento'].map(
              (item) => (
                <article key={item}>
                  <CheckCircle2 size={16} />
                  <span>{item}</span>
                </article>
              ),
            )}
          </div>
        </ExecutiveCard>
      </section>
    </>
  );
}

const renderers: Record<ViewId, (context: ObservatoryContext) => JSX.Element> = {
  'Home ejecutivo': (context) => <ExecutiveHome {...context} />,
  Especializacion: (context) => <SpecializationView {...context} />,
  'Benchmarking SNIES': (context) => <BenchmarkingView {...context} />,
  Empleabilidad: (context) => <EmployabilityView {...context} />,
  'Reescritura IA': (context) => <RewriteView {...context} />,
  'Comite academico': (context) => <CommitteeView {...context} />,
  'Detalle microcurricular': (context) => <MicroDetailView {...context} />,
  'Dashboard institucional': (context) => <InstitutionalDashboardView {...context} />,
};

export function InstitutionalObservatoryPage() {
  const [activeView, setActiveView] = useState<ViewId>('Home ejecutivo');
  const [selectedSpecialization, setSelectedSpecialization] = useState<SpecializationOption | null>(null);
  const [documents, setDocuments] = useState<MicrocurriculumDocument[]>([]);
  const [analysis, setAnalysis] = useState<SpecializationMicroAnalysis | null>(null);
  const [relatedPrograms, setRelatedPrograms] = useState<RelatedUniversityProgram[]>([]);
  const [rewriteResult, setRewriteResult] = useState<SpecializationRewriteResponse | null>(null);
  const [rewriting, setRewriting] = useState(false);
  const [dataState, setDataState] = useState<ObservatoryDataState>('loading');
  const [message, setMessage] = useState('Cargando datos reales del observatorio...');

  async function loadLiveData() {
    setDataState('loading');
    setMessage('Cargando especializaciones, documentos y analisis curricular real...');
    try {
      const specs = await getSpecializations();
      const visual =
        specs.find((item) => normalizeText(item.nombre).includes('visual analytics')) ||
        specs.find((item) => normalizeText(item.nombre).includes('big data')) ||
        specs[0] ||
        null;
      setSelectedSpecialization(visual);
      if (!visual) {
        setDataState('demo');
        setMessage('No se encontraron especializaciones reales; se mantiene una maqueta demo.');
        return;
      }
      const [docs, consolidated, related] = await Promise.all([
        getSpecializationMicrocurriculumDocuments(visual.id).catch(() => ({ specialization: visual.nombre, documents: [] })),
        analyzeSpecializationMicrocurriculums(visual.id).catch(() => null),
        Number.isFinite(Number(visual.id))
          ? getRelatedUniversityPrograms(Number(visual.id), 8).catch(() => ({ items: [] }))
          : Promise.resolve({ items: [] }),
      ]);
      setDocuments(docs.documents || []);
      setAnalysis(consolidated);
      setRelatedPrograms(related.items || []);
      if (consolidated) {
        setDataState(related.items?.length ? 'live' : 'partial');
        setMessage(
          related.items?.length
            ? 'Datos reales cargados: microcurriculos, analisis curricular y comparables SNIES.'
            : 'Datos reales cargados parcialmente: microcurriculos y analisis curricular; benchmarking con respaldo demo.',
        );
      } else {
        setDataState('partial');
        setMessage('Especializacion y documentos reales cargados; el analisis curricular no respondio y se usa respaldo demo.');
      }
    } catch {
      setDataState('demo');
      setMessage('No fue posible contactar la API; se conserva respaldo demo para revisar la experiencia.');
    }
  }

  async function handleRewrite() {
    if (!selectedSpecialization) return;
    setRewriting(true);
    try {
      const result = await rewriteSpecializationMicrocurriculums(selectedSpecialization.id);
      setRewriteResult(result);
      setDataState('live');
      setMessage('Reescritura real generada desde los microcurriculos de la especializacion activa.');
    } catch {
      setMessage('No fue posible generar la reescritura real; se mantiene la propuesta visual de respaldo.');
    } finally {
      setRewriting(false);
    }
  }

  useEffect(() => {
    void loadLiveData();
  }, []);

  const context: ObservatoryContext = {
    analysis,
    documents,
    relatedPrograms,
    selectedSpecialization,
    rewriteResult,
    rewriting,
    dataState,
    message,
    refresh: loadLiveData,
    rewrite: handleRewrite,
  };

  const ActiveView = useMemo(() => renderers[activeView], [activeView]);

  return (
    <main className="oi-shell">
      <aside className="oi-sidebar">
        <div className="oi-brand">
          <strong>UNIR</strong>
          <span>Observatorio Institucional de Inteligencia Curricular</span>
        </div>
        <nav aria-label="Vistas del observatorio">
          {navItems.map((item) => {
            const Icon = viewIcons[item];
            return (
              <button
                key={item}
                className={activeView === item ? 'active' : ''}
                type="button"
                onClick={() => setActiveView(item)}
              >
                <Icon size={17} />
                {item}
              </button>
            );
          })}
        </nav>
        <div className="oi-sidebar-footer">
          <ShieldCheck size={18} />
          <div>
            <span>Corte institucional</span>
            <strong>Mayo 2026 - Consejo academico</strong>
          </div>
        </div>
      </aside>
      <section className="oi-workspace">
        <header className="oi-topbar">
          <div>
            <span>Universidad Internacional de La Rioja</span>
            <strong>Portafolio - Posgrado - Colombia</strong>
          </div>
          <div className="oi-topbar-actions">
            <StatusMark tone={dataState === 'live' ? 'green' : dataState === 'demo' ? 'amber' : 'blue'}>
              {dataState === 'live' ? 'Datos reales' : dataState === 'demo' ? 'Modo demo' : 'Datos parciales'}
            </StatusMark>
            <button type="button" onClick={loadLiveData}>
              <LineChart size={16} />
              Actualizar
            </button>
          </div>
        </header>
        <div className="oi-content">
          {ActiveView(context)}
        </div>
      </section>
      <div className="oi-mobile-note">
        <Building2 size={18} />
        <span>Vista optimizada para desktop ejecutivo. En movil se conserva lectura secuencial.</span>
      </div>
      <Network className="oi-watermark" aria-hidden="true" />
    </main>
  );
}
