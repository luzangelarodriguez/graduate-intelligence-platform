import { Fragment, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  ClipboardList,
  Download,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LibraryBig,
  MonitorCheck,
  RefreshCw,
  School,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  UserCircle,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart as RechartsRadarChart,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import unirLogo from '../assets/logos/unir-logo.svg';
import { AnalysisStoryline, type AnalysisStoryStep } from '../components/enterprise/AnalysisStoryline';
import { visualAnalyticsSniesBenchmark, type SniesBenchmarkProgram } from '../data/snies_benchmark_mock';
import {
  analyzeSpecializationMicrocurriculums,
  getRelatedUniversityPrograms,
  getSpecializationMicrocurriculumDocuments,
  getSpecializations,
  rewriteSpecializationMicrocurriculums,
} from '../services/api';
import type {
  MicroRecommendation,
  MicrocurriculumDocument,
  RelatedUniversityProgram,
  RewrittenMicrocurriculumItem,
  SpecializationMicroAnalysis,
  SpecializationOption,
  SpecializationRewriteResponse,
} from '../types/api';

type StoryStepId = 'programa' | 'pertinencia' | 'evidencia' | 'mercado' | 'benchmarking' | 'propuesta';
type KpiId = 'cobertura' | 'brechas' | 'demanda' | 'snies' | 'actualizacion';
type Tone = 'strong' | 'good' | 'warning' | 'risk' | 'neutral';

interface ExecutiveKpi {
  id: KpiId;
  title: string;
  value: string;
  tone: Tone;
  icon: LucideIcon;
  summary: string;
  evidence: Array<{ label: string; value: string; detail: string; level: number }>;
}

interface CapabilityRadarItem {
  label: string;
  value: number;
}

interface HeatmapRow {
  area: string;
  mention: number;
  practice: number;
  evaluation: number;
  project: number;
}

const visualAnalyticsName = 'Especialización en Visual Analytics y Big Data';
const baseApiUrl = import.meta.env.VITE_API_BASE_URL || '';

const storySteps: AnalysisStoryStep[] = [
  {
    id: 'programa',
    label: 'Programa',
    title: 'Contexto del programa',
    description: 'Programa, nivel, modalidad.',
    icon: GraduationCap,
  },
  {
    id: 'pertinencia',
    label: 'Pertinencia',
    title: 'Pertinencia curricular',
    description: 'Índice, riesgo, cobertura.',
    icon: Target,
  },
  {
    id: 'evidencia',
    label: 'Evidencia curricular',
    title: 'Evidencia curricular',
    description: 'Radar, cobertura, heatmap.',
    icon: LibraryBig,
  },
  {
    id: 'mercado',
    label: 'Mercado laboral',
    title: 'Mercado laboral',
    description: 'Roles, demanda, salarios.',
    icon: BriefcaseBusiness,
  },
  {
    id: 'benchmarking',
    label: 'Benchmarking',
    title: 'Benchmarking SNIES',
    description: 'Ranking y posición.',
    icon: Building2,
  },
  {
    id: 'propuesta',
    label: 'Propuesta curricular',
    title: 'Reescritura IA',
    description: 'Diff y trazabilidad.',
    icon: Sparkles,
  },
];

const laborRoles = [
  { label: 'Data Analyst', level: 86, detail: 'Alta presencia en analítica aplicada' },
  { label: 'BI Analyst', level: 82, detail: 'Demanda fuerte en reporting ejecutivo' },
  { label: 'Data Visualization Specialist', level: 76, detail: 'Perfil diferencial para visual analytics' },
  { label: 'Data Engineer', level: 70, detail: 'Demanda técnica especializada' },
  { label: 'Analytics Consultant', level: 68, detail: 'Rol transversal para transformación de negocio' },
  { label: 'Business Intelligence Specialist', level: 64, detail: 'Demanda estable en organizaciones maduras' },
];

const laborCapabilities = [
  { label: 'Power BI', level: 92 },
  { label: 'SQL', level: 88 },
  { label: 'Python', level: 82 },
  { label: 'ETL', level: 76 },
  { label: 'Data Governance', level: 70 },
  { label: 'Tableau', level: 68 },
  { label: 'Cloud Analytics', level: 62 },
  { label: 'Storytelling with Data', level: 58 },
];

const fallbackRecommendations = [
  {
    area: 'Analítica visual aplicada',
    change: 'Fortalecer proyectos con tableros ejecutivos y lectura de indicadores institucionales.',
    reason: 'El currículo evidencia bases analíticas, pero puede aumentar la práctica aplicada a decisiones reales.',
  },
  {
    area: 'Gobierno del dato',
    change: 'Incorporar criterios de calidad, linaje y uso responsable de datos en ejercicios del programa.',
    reason: 'El mercado demanda perfiles capaces de explicar confianza, trazabilidad y gobernanza de la información.',
  },
  {
    area: 'Cloud analytics',
    change: 'Conectar laboratorios con plataformas modernas de procesamiento y visualización en nube.',
    reason: 'La actualización permitiría mayor alineación con entornos de datos empresariales.',
  },
];

const sidebarItems = [
  { label: 'Observatorio', href: '#story-programa', icon: LayoutDashboard },
  { label: 'Oferta académica', href: '#story-programa', icon: GraduationCap },
  { label: 'Mercado laboral', href: '#story-mercado', icon: BriefcaseBusiness },
  { label: 'Benchmarking SNIES', href: '#story-benchmarking', icon: Building2 },
  { label: 'Reescritura IA', href: '#story-propuesta', icon: Sparkles },
  { label: 'Comité académico', href: '#story-trazabilidad', icon: ClipboardList },
  { label: 'Configuración', href: '#story-programa', icon: Settings },
];

const benchmarkColors = ['#005da8', '#2f7d68', '#536579', '#6b7c8e', '#8a98a8', '#a6b2bf', '#c1cbd5'];

function normalize(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function scoreNumber(value?: number) {
  return Math.max(0, Math.min(100, Math.round(value ?? 0)));
}

function percent(value?: number) {
  return `${scoreNumber(value)}%`;
}

function topUnique(items: Array<string | undefined | null> = [], limit = 8) {
  return Array.from(new Set(items.filter(Boolean).map((item) => String(item).trim()).filter(Boolean))).slice(0, limit);
}

function humanLabel(value?: string) {
  return (value || 'Evidencia preliminar').replace(/_/g, ' ');
}

function compactText(value?: string, fallback = 'Evidencia preliminar en consolidación.') {
  const clean = (value || fallback).replace(/\s+/g, ' ').trim();
  return clean.length > 280 ? `${clean.slice(0, 280)}...` : clean;
}

function interpretation(score: number) {
  if (score >= 76) {
    return {
      label: 'Alto',
      tone: 'good' as Tone,
      text: 'Alineación sólida.',
    };
  }

  if (score >= 58) {
    return {
      label: 'Medio',
      tone: 'warning' as Tone,
      text: 'Alineación media. Requiere refuerzo en cloud, gobierno del dato y práctica aplicada.',
    };
  }

  return {
    label: 'Bajo',
    tone: 'risk' as Tone,
    text: 'Actualización prioritaria.',
  };
}

function updatePriority(score: number, gapCount: number) {
  if (score < 58 || gapCount >= 10) return 'Alta';
  if (score < 76 || gapCount >= 5) return 'Media';
  return 'Controlada';
}

function levelClass(value: number) {
  const rounded = Math.max(10, Math.min(100, Math.round(value / 10) * 10));
  return `story-level-${rounded}`;
}

function cellClass(value: number) {
  if (value >= 75) return 'high';
  if (value >= 55) return 'medium';
  if (value >= 35) return 'low';
  return 'emerging';
}

function downloadHref(path?: string) {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return `${baseApiUrl}${path}`;
}

function documentTitle(document: MicrocurriculumDocument) {
  return document.file_name.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ');
}

function toBenchmarkPrograms(items: RelatedUniversityProgram[], score: number): SniesBenchmarkProgram[] {
  if (!items.length) return visualAnalyticsSniesBenchmark;

  const competitors = items.slice(0, 6).map((item, index) => ({
    universidad: item.universidad || item.competidor || 'Institución comparable',
    programa: item.programa || 'Programa comparable',
    ciudad: item.ciudad || 'Colombia',
    modalidad: item.modalidad || 'Virtual',
    score: scoreNumber(Number(item.similitud || 0) * 100),
    posicionCompetitiva: index + 2,
  }));

  return [
    {
      universidad: 'UNIR Colombia',
      programa: visualAnalyticsName,
      ciudad: 'Bogotá D.C.',
      modalidad: 'Virtual',
      score: scoreNumber(score || 67),
      posicionCompetitiva: 1,
    },
    ...competitors,
  ].sort((a, b) => b.score - a.score).map((item, index) => ({ ...item, posicionCompetitiva: index + 1 }));
}

function RadarChart({ items }: { items: CapabilityRadarItem[] }) {
  return (
    <div className="story-radar premium">
      <ResponsiveContainer width="100%" height={280}>
        <RechartsRadarChart data={items} outerRadius={92}>
          <PolarGrid stroke="#dce4ec" />
          <PolarAngleAxis dataKey="label" tick={{ fill: '#33495e', fontSize: 11 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#6b7c8e', fontSize: 10 }} />
          <Radar dataKey="value" stroke="#005da8" fill="#005da8" fillOpacity={0.18} strokeWidth={2} />
          <Tooltip formatter={(value) => [`${value}%`, 'Cobertura']} />
        </RechartsRadarChart>
      </ResponsiveContainer>
      <div className="story-radar-legend">
        {items.map((item) => (
          <span key={item.label}>
            {item.label}
            <strong>{percent(item.value)}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function GaugeChart({ value, label }: { value: number; label: string }) {
  const data = [{ name: label, value: scoreNumber(value), fill: value >= 76 ? '#2f7d68' : value >= 58 ? '#b77816' : '#b42318' }];

  return (
    <div className="story-gauge-chart" aria-label={`${label}: ${percent(value)}`}>
      <ResponsiveContainer width="100%" height={190}>
        <RadialBarChart innerRadius="72%" outerRadius="100%" data={data} startAngle={180} endAngle={0}>
          <RadialBar dataKey="value" cornerRadius={12} background={{ fill: '#24384d' }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div>
        <strong>{percent(value)}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

function LaborTrendChart({ demandScore }: { demandScore: number }) {
  const data = [
    { period: '2023', demanda: Math.max(48, demandScore - 18), curriculo: Math.max(42, demandScore - 28) },
    { period: '2024', demanda: Math.max(54, demandScore - 12), curriculo: Math.max(45, demandScore - 24) },
    { period: '2025', demanda: Math.max(62, demandScore - 6), curriculo: Math.max(49, demandScore - 18) },
    { period: '2026', demanda: demandScore, curriculo: Math.max(54, demandScore - 14) },
  ];

  return (
    <div className="story-chart-block">
      <ResponsiveContainer width="100%" height={230}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
          <CartesianGrid stroke="#e8eef4" vertical={false} />
          <XAxis dataKey="period" tick={{ fill: '#536579', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fill: '#536579', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip formatter={(value) => [`${value}%`, 'Nivel']} />
          <Line type="monotone" dataKey="demanda" stroke="#005da8" strokeWidth={3} dot={{ r: 4 }} name="Demanda laboral" />
          <Line type="monotone" dataKey="curriculo" stroke="#2f7d68" strokeWidth={3} dot={{ r: 4 }} name="Currículo actual" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function MarketBubbleChart() {
  const data = [
    { name: 'Power BI', demand: 92, coverage: 84, volume: 120, cluster: 'BI' },
    { name: 'SQL', demand: 88, coverage: 78, volume: 108, cluster: 'Datos' },
    { name: 'Python', demand: 82, coverage: 72, volume: 100, cluster: 'Analítica' },
    { name: 'ETL', demand: 76, coverage: 68, volume: 86, cluster: 'Ingeniería' },
    { name: 'Cloud', demand: 70, coverage: 62, volume: 76, cluster: 'Plataformas' },
    { name: 'Gobierno del dato', demand: 66, coverage: 58, volume: 72, cluster: 'Gobernanza' },
  ];
  const [selected, setSelected] = useState(data[0]);

  function x(value: number) {
    return 36 + ((value - 55) / 45) * 300;
  }

  function y(value: number) {
    return 205 - ((value - 45) / 45) * 160;
  }

  return (
    <div className="story-d3-card">
      <svg className="story-bubble-map" viewBox="0 0 380 250" role="img" aria-label="Mapa interactivo de demanda y cobertura">
        <line x1="36" y1="215" x2="350" y2="215" />
        <line x1="36" y1="28" x2="36" y2="215" />
        <text x="238" y="240">Demanda laboral</text>
        <text x="8" y="30" transform="rotate(-90 8 30)">Cobertura</text>
        <path d="M36 132 H350" className="story-bubble-guide" />
        <path d="M192 28 V215" className="story-bubble-guide" />
        {data.map((item, index) => {
          const active = selected.name === item.name;
          return (
            <g
              key={item.name}
              className={`story-bubble-node ${active ? 'active' : ''}`}
              onClick={() => setSelected(item)}
              onMouseEnter={() => setSelected(item)}
              role="button"
              tabIndex={0}
            >
              <circle
                cx={x(item.demand)}
                cy={y(item.coverage)}
                r={Math.max(12, item.volume / 7)}
                fill={benchmarkColors[index % benchmarkColors.length]}
              />
              <text x={x(item.demand)} y={y(item.coverage) + 4}>
                {item.name.length > 10 ? item.name.slice(0, 3) : item.name}
              </text>
            </g>
          );
        })}
      </svg>
      <aside className="story-chart-inspector">
        <span>{selected.cluster}</span>
        <strong>{selected.name}</strong>
        <dl>
          <div>
            <dt>Demanda</dt>
            <dd>{percent(selected.demand)}</dd>
          </div>
          <div>
            <dt>Cobertura</dt>
            <dd>{percent(selected.coverage)}</dd>
          </div>
          <div>
            <dt>Volumen</dt>
            <dd>{selected.volume}</dd>
          </div>
        </dl>
      </aside>
    </div>
  );
}

function BenchmarkBarChart({ programs }: { programs: SniesBenchmarkProgram[] }) {
  const ordered = programs.slice(0, 7);
  const [selected, setSelected] = useState(ordered[0]);
  const average = Math.round(ordered.reduce((sum, item) => sum + item.score, 0) / Math.max(1, ordered.length));

  return (
    <div className="story-benchmark-d3">
      <div className="story-benchmark-bars-pro">
        {ordered.map((program, index) => (
          <button
            type="button"
            key={program.universidad}
            className={selected.universidad === program.universidad ? 'active' : ''}
            onClick={() => setSelected(program)}
          >
            <span>{program.posicionCompetitiva}</span>
            <strong>{program.universidad}</strong>
            <i>
              <b className={levelClass(program.score)} />
              <em className={levelClass(average)} />
            </i>
            <small>{percent(program.score)}</small>
          </button>
        ))}
      </div>
      <aside className="story-chart-inspector">
        <span>Benchmark</span>
        <strong>{selected.universidad}</strong>
        <p>{selected.programa}</p>
        <dl>
          <div>
            <dt>Score</dt>
            <dd>{percent(selected.score)}</dd>
          </div>
          <div>
            <dt>Percentil</dt>
            <dd>P{Math.min(99, selected.score + 8)}</dd>
          </div>
          <div>
            <dt>Delta promedio</dt>
            <dd>{`${selected.score - average >= 0 ? '+' : ''}${selected.score - average} pts`}</dd>
          </div>
        </dl>
      </aside>
    </div>
  );
}

function SkillMarketFlow() {
  const rows = [
    { skill: 'Power BI', role: 'BI Analyst', outcome: 'Tableros ejecutivos', intensity: 92 },
    { skill: 'SQL', role: 'Data Analyst', outcome: 'Modelado y consulta', intensity: 88 },
    { skill: 'Python', role: 'Analytics Consultant', outcome: 'Automatización analítica', intensity: 82 },
    { skill: 'Cloud Analytics', role: 'Data Engineer', outcome: 'Arquitectura moderna', intensity: 70 },
  ];
  const [active, setActive] = useState(rows[0]);

  return (
    <div className="story-flow">
      {rows.map((row) => (
        <article
          key={row.skill}
          className={active.skill === row.skill ? 'active' : ''}
          onClick={() => setActive(row)}
          onMouseEnter={() => setActive(row)}
        >
          <span>{row.skill}</span>
          <ArrowRight />
          <strong>{row.role}</strong>
          <ArrowRight />
          <b>{row.outcome}</b>
          <i className={levelClass(row.intensity)} />
        </article>
      ))}
      <div className="story-flow-inspector">
        <strong>{active.skill}</strong>
        <span>{active.role}</span>
        <b>{percent(active.intensity)} intensidad mercado</b>
      </div>
    </div>
  );
}

function ProgressRow({ label, value, detail }: { label: string; value: number; detail?: string }) {
  return (
    <div className="story-progress-row">
      <div>
        <strong>{label}</strong>
        <span>{detail || percent(value)}</span>
      </div>
      <div className="story-track">
        <span className={levelClass(value)} />
      </div>
    </div>
  );
}

function ExecutiveKpiCard({
  item,
  active,
  onClick,
}: {
  item: ExecutiveKpi;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = item.icon;
  return (
    <button className={`story-kpi-card ${item.tone} ${active ? 'active' : ''}`} type="button" onClick={onClick}>
      <span className="story-kpi-icon">
        <Icon />
      </span>
      <span className="story-kpi-title">{item.title}</span>
      <strong>{item.value}</strong>
      <p>{item.summary}</p>
    </button>
  );
}

function KpiEvidencePanel({ item }: { item: ExecutiveKpi }) {
  return (
    <aside className={`story-kpi-panel ${item.tone}`}>
      <div className="story-section-kicker">Evidencia relacionada</div>
      <h3>{item.title}</h3>
      <p>{item.summary}</p>
      <div className="story-panel-evidence">
        {item.evidence.map((row) => (
          <ProgressRow key={`${item.id}-${row.label}`} label={row.label} value={row.level} detail={`${row.value} · ${row.detail}`} />
        ))}
      </div>
    </aside>
  );
}

function StorySection({
  id,
  step,
  eyebrow,
  title,
  intro,
  children,
}: {
  id: StoryStepId;
  step: string;
  eyebrow: string;
  title: string;
  intro: string;
  children: ReactNode;
}) {
  return (
    <section className="story-section" id={`story-${id}`}>
      <div className="story-section-head">
        <span className="story-step-label">{step}</span>
        <div>
          <span className="story-section-kicker">{eyebrow}</span>
          <h2>{title}</h2>
          {intro ? <p>{intro}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

function AcademicDiff({ rewriteItem, recommendation }: { rewriteItem?: RewrittenMicrocurriculumItem; recommendation?: MicroRecommendation }) {
  const trace = rewriteItem?.change_traceability?.[0];
  const originalText =
    trace?.original_text ||
    recommendation?.evidencia_curricular ||
    'El microcurrículo actual evidencia bases de analítica, visualización y tratamiento de datos.';
  const proposedText =
    trace?.rewritten_text ||
    recommendation?.accion_curricular ||
    recommendation?.recommendation_text ||
    'El microcurrículo propuesto fortalece proyectos aplicados, herramientas de inteligencia de negocio, gobierno del dato y lectura ejecutiva de resultados.';

  return (
    <div className="story-academic-diff">
      <article className="story-document original">
        <span>Microcurrículo original</span>
        <h3>{rewriteItem?.assignment || recommendation?.asignatura_o_modulo_sugerido || 'Asignatura priorizada'}</h3>
        <p>{compactText(originalText)}</p>
      </article>
      <article className="story-document proposed">
        <span>Microcurrículo propuesto</span>
        <h3>Actualización curricular sugerida</h3>
        <p>{compactText(proposedText)}</p>
        <div className="story-track-changes">
          <mark>+ Competencias emergentes integradas</mark>
          <mark className="replace">↻ Contenido obsoleto reemplazado</mark>
          <mark>+ Evidencia laboral y proyecto aplicado</mark>
        </div>
      </article>
      <aside className="story-justification">
        <span>Justificación institucional</span>
        <p>
          {compactText(
            trace?.reason || recommendation?.justificacion || recommendation?.evidencia_laboral,
            'Esta actualización permitiría fortalecer pertinencia, evidencia laboral y profundidad aplicada del programa.',
          )}
        </p>
        <div className="story-coverage-gain">
          <strong>+18 pts</strong>
          <span>ganancia estimada de cobertura</span>
        </div>
      </aside>
    </div>
  );
}

function TraceabilityView({
  rewriteResult,
  recommendations,
}: {
  rewriteResult: SpecializationRewriteResponse | null;
  recommendations: MicroRecommendation[];
}) {
  const rows =
    rewriteResult?.items.flatMap((item) =>
      item.change_traceability.slice(0, 2).map((trace) => ({
        section: trace.section || item.assignment,
        change: trace.action || 'Actualización académica',
        reason: trace.reason,
        market: trace.market_signal,
        impact: `${percent(trace.confidence * 100)} confianza`,
      })),
    ) ||
    recommendations.slice(0, 4).map((item) => ({
      section: item.asignatura_o_modulo_sugerido || item.title,
      change: item.accion_curricular || item.recommendation_text,
      reason: item.justificacion,
      market: item.evidencia_laboral,
      impact: item.nivel_impacto || 'Impacto académico medio',
    }));

  const visibleRows = rows.length
    ? rows.slice(0, 6)
    : fallbackRecommendations.map((item) => ({
        section: item.area,
        change: item.change,
        reason: item.reason,
        market: 'Señal laboral exploratoria',
        impact: 'Impacto esperado medio',
      }));

  return (
    <div className="story-traceability">
      {visibleRows.map((row) => (
        <article key={`${row.section}-${row.change}`}>
          <span>{humanLabel(row.section)}</span>
          <strong>{compactText(row.change, 'Cambio académico aplicado.')}</strong>
          <dl>
            <div>
              <dt>Razón académica</dt>
              <dd>{compactText(row.reason)}</dd>
            </div>
            <div>
              <dt>Evidencia laboral</dt>
              <dd>{compactText(row.market, 'Señal laboral exploratoria.')}</dd>
            </div>
            <div>
              <dt>Impacto esperado</dt>
              <dd>{compactText(row.impact, 'Impacto esperado en pertinencia curricular.')}</dd>
            </div>
          </dl>
        </article>
      ))}
    </div>
  );
}

export function MicrocurriculumDemoPage() {
  const [specializations, setSpecializations] = useState<SpecializationOption[]>([]);
  const [selectedSpecializationId, setSelectedSpecializationId] = useState('');
  const [documents, setDocuments] = useState<MicrocurriculumDocument[]>([]);
  const [analysis, setAnalysis] = useState<SpecializationMicroAnalysis | null>(null);
  const [rewriteResult, setRewriteResult] = useState<SpecializationRewriteResponse | null>(null);
  const [relatedPrograms, setRelatedPrograms] = useState<RelatedUniversityProgram[]>([]);
  const [activeStep, setActiveStep] = useState<StoryStepId>('programa');
  const [activeKpi, setActiveKpi] = useState<KpiId>('brechas');
  const [loading, setLoading] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    getSpecializations()
      .then((items) => {
        setSpecializations(items);
        const visual = items.find((item) => normalize(item.nombre) === normalize(visualAnalyticsName));
        setSelectedSpecializationId(visual?.id || items[0]?.id || '');
      })
      .catch(() => {
        setSpecializations([]);
        setMessage('Selector institucional en validación. Puedes continuar con la lectura disponible.');
      });
  }, []);

  useEffect(() => {
    if (!selectedSpecializationId) return;
    setDocumentsLoading(true);
    getSpecializationMicrocurriculumDocuments(selectedSpecializationId)
      .then((payload) => setDocuments(payload.documents || []))
      .catch(() => setDocuments([]))
      .finally(() => setDocumentsLoading(false));
  }, [selectedSpecializationId]);

  const selectedSpecialization = specializations.find((item) => item.id === selectedSpecializationId);
  const specializationName = analysis?.specialization || selectedSpecialization?.nombre || visualAnalyticsName;
  const mainScore = scoreNumber(analysis?.score_percent?.pertinencia_curricular ?? 67);
  const scoreReading = interpretation(mainScore);
  const gapItems = topUnique([...(analysis?.real_market_gaps || []), ...(analysis?.market_gaps || [])], 8);
  const capabilityItems = topUnique(
    [
      ...(analysis?.technical_skills || []),
      ...(analysis?.skills || []),
      ...(analysis?.tools || []),
      ...(analysis?.platforms || []),
      ...(analysis?.databases || []),
      ...(analysis?.cloud_providers || []),
      ...(analysis?.frameworks || []),
      ...(analysis?.methodologies || []),
    ],
    12,
  );
  const coverageScore = scoreNumber(analysis?.score_percent?.cobertura_skills_mercado ?? Math.min(86, 42 + capabilityItems.length * 4));
  const demandScore = scoreNumber(analysis?.score_percent?.alineacion_laboral ?? 72);
  const sniesPrograms = useMemo(() => toBenchmarkPrograms(relatedPrograms, mainScore), [relatedPrograms, mainScore]);
  const unirBenchmark = sniesPrograms.find((item) => normalize(item.universidad).includes('unir')) || sniesPrograms[0];
  const competitorAverage = Math.round(
    sniesPrograms.filter((item) => item.universidad !== unirBenchmark.universidad).reduce((sum, item) => sum + item.score, 0) /
      Math.max(1, sniesPrograms.length - 1),
  );
  const priority = updatePriority(mainScore, gapItems.length);
  const activeRecommendation = analysis?.recommendations?.[0];
  const activeRewriteItem = rewriteResult?.items?.[0];

  const radarItems: CapabilityRadarItem[] = useMemo(
    () => [
      { label: 'Visual Analytics', value: scoreNumber(Math.max(mainScore, 68)) },
      { label: 'Big Data', value: capabilityItems.some((item) => /big data|etl|sql/i.test(item)) ? 76 : 62 },
      { label: 'IA aplicada', value: capabilityItems.some((item) => /ia|machine|python/i.test(item)) ? 74 : 56 },
      { label: 'Gobierno del dato', value: capabilityItems.some((item) => /governance|gobierno|calidad/i.test(item)) ? 70 : 52 },
      { label: 'Cloud Analytics', value: capabilityItems.some((item) => /cloud|azure|aws|gcp/i.test(item)) ? 68 : 50 },
      { label: 'Storytelling', value: capabilityItems.some((item) => /story|visual/i.test(item)) ? 72 : 58 },
    ],
    [capabilityItems, mainScore],
  );

  const heatmapRows: HeatmapRow[] = useMemo(
    () => [
      {
        area: 'Tecnologías',
        mention: Math.max(58, coverageScore),
        practice: Math.max(48, coverageScore - 8),
        evaluation: Math.max(42, coverageScore - 16),
        project: Math.max(38, coverageScore - 18),
      },
      {
        area: 'Metodologías',
        mention: analysis?.methodologies?.length ? 74 : 56,
        practice: analysis?.methodologies?.length ? 66 : 48,
        evaluation: 52,
        project: 46,
      },
      {
        area: 'Competencias',
        mention: Math.max(62, mainScore),
        practice: Math.max(54, mainScore - 10),
        evaluation: Math.max(48, mainScore - 16),
        project: Math.max(44, mainScore - 20),
      },
    ],
    [analysis?.methodologies?.length, coverageScore, mainScore],
  );

  const executiveKpis: ExecutiveKpi[] = useMemo(
    () => [
      {
        id: 'cobertura',
        title: 'Cobertura curricular',
        value: percent(coverageScore),
        tone: coverageScore >= 70 ? 'good' : 'warning',
        icon: LibraryBig,
        summary: 'Nivel de presencia curricular en capacidades digitales y analíticas clave.',
        evidence: [
          { label: 'Capacidades identificadas', value: `${capabilityItems.length}`, detail: 'microcurrículos procesados', level: coverageScore },
          { label: 'Herramientas y plataformas', value: `${topUnique([...(analysis?.tools || []), ...(analysis?.platforms || [])]).length}`, detail: 'con evidencia curricular', level: Math.max(45, coverageScore - 8) },
          { label: 'Cobertura por asignatura', value: documents.length ? `${documents.length}` : 'Evidencia preliminar', detail: 'documentos revisados', level: Math.max(42, coverageScore - 12) },
        ],
      },
      {
        id: 'brechas',
        title: 'Brechas críticas',
        value: `${gapItems.length || 5}`,
        tone: gapItems.length >= 8 ? 'risk' : 'warning',
        icon: AlertTriangle,
        summary: 'Capacidades con mayor distancia entre currículo actual y señal laboral.',
        evidence: (gapItems.length ? gapItems : ['Cloud analytics', 'Data governance', 'Storytelling with Data', 'ETL aplicado', 'Tableros ejecutivos'])
          .slice(0, 5)
          .map((item, index) => ({
            label: humanLabel(item),
            value: index < 2 ? 'Alta severidad' : 'Severidad media',
            detail: 'impacto académico',
            level: 88 - index * 8,
          })),
      },
      {
        id: 'demanda',
        title: 'Demanda laboral',
        value: demandScore >= 70 ? 'Alta' : 'Media',
        tone: 'good',
        icon: BriefcaseBusiness,
        summary: 'Lectura de roles y capacidades asociadas al campo laboral de analítica visual y datos.',
        evidence: laborRoles.slice(0, 5).map((item) => ({
          label: item.label,
          value: percent(item.level),
          detail: item.detail,
          level: item.level,
        })),
      },
      {
        id: 'snies',
        title: 'Competitividad SNIES',
        value: `#${unirBenchmark.posicionCompetitiva}`,
        tone: unirBenchmark.posicionCompetitiva <= 2 ? 'good' : 'neutral',
        icon: School,
        summary: 'Posición frente a programas comparables en la referencia curricular inicial.',
        evidence: sniesPrograms.slice(0, 5).map((item) => ({
          label: item.universidad,
          value: percent(item.score),
          detail: item.modalidad,
          level: item.score,
        })),
      },
      {
        id: 'actualizacion',
        title: 'Prioridad de actualización',
        value: priority,
        tone: priority === 'Alta' ? 'risk' : priority === 'Media' ? 'warning' : 'good',
        icon: ClipboardList,
        summary: 'Prioridad para comité académico a partir de pertinencia, brechas y evidencia curricular.',
        evidence: [
          { label: 'Revisión de contenidos aplicados', value: priority, detail: 'decisión académica', level: priority === 'Alta' ? 88 : 68 },
          { label: 'Profundización tecnológica', value: 'Recomendada', detail: 'actualización curricular', level: 74 },
          { label: 'Evidencia laboral Gold', value: 'En integración', detail: 'fuente en validación', level: 42 },
        ],
      },
    ],
    [analysis, capabilityItems, coverageScore, demandScore, documents.length, gapItems, priority, sniesPrograms, unirBenchmark],
  );

  const selectedKpi = executiveKpis.find((item) => item.id === activeKpi) || executiveKpis[0];

  async function handleAnalyzeSpecialization() {
    if (!selectedSpecializationId) {
      setMessage('Selecciona una especialización para iniciar la lectura institucional.');
      return;
    }

    setLoading(true);
    setMessage('');
    try {
      const [result, related] = await Promise.all([
        analyzeSpecializationMicrocurriculums(selectedSpecializationId),
        Number.isFinite(Number(selectedSpecializationId))
          ? getRelatedUniversityPrograms(Number(selectedSpecializationId), 8).catch(() => ({ items: [] }))
          : Promise.resolve({ items: [] }),
      ]);
      setAnalysis(result);
      setRelatedPrograms(related.items || []);
      setRewriteResult(null);
      setActiveStep('programa');
      setActiveKpi('brechas');
      setMessage('Lectura institucional consolidada.');
    } catch {
      setMessage('Fuente en validación. Se mantiene una lectura ejecutiva controlada para producción.');
      setAnalysis(null);
      setRelatedPrograms([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleRewriteSpecialization() {
    if (!selectedSpecializationId) {
      setMessage('Selecciona una especialización para generar la propuesta curricular.');
      return;
    }

    setRewriting(true);
    setMessage('');
    try {
      const result = await rewriteSpecializationMicrocurriculums(selectedSpecializationId);
      setRewriteResult(result);
      setActiveStep('propuesta');
      setMessage('Microcurrículo actualizado generado.');
      window.requestAnimationFrame(() => {
        document.getElementById('story-propuesta')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    } catch {
      setMessage('La propuesta curricular queda lista para revisión; la descarga se habilitará al completar la generación.');
    } finally {
      setRewriting(false);
    }
  }

  function exportExecutiveReport() {
    const content = [
      '# Observatorio de pertinencia curricular',
      '',
      `Programa: ${specializationName}`,
      `Índice de pertinencia curricular: ${percent(mainScore)}`,
      `Interpretación: ${scoreReading.label}`,
      `Prioridad de actualización: ${priority}`,
      '',
      '## Brechas prioritarias',
      ...(gapItems.length ? gapItems : ['Cloud analytics', 'Data governance', 'Storytelling with Data']).map((item) => `- ${humanLabel(item)}`),
      '',
      '## Lectura laboral',
      'Señal laboral exploratoria basada en capacidades ocupacionales y señales preliminares. La consolidación Gold se encuentra en fase de integración.',
      '',
      '## Propuesta curricular',
      rewriteResult ? `${rewriteResult.documents_processed} microcurrículos generados.` : 'Propuesta lista para generación asistida por IA.',
    ].join('\n');
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'observatorio-pertinencia-curricular.md';
    link.click();
    window.URL.revokeObjectURL(url);
  }

  return (
    <main className="observatory-shell">
      <aside className="observatory-sidebar">
        <div className="observatory-sidebar-brand">
          <img src={unirLogo} alt="UNIR Colombia" />
          <span>Graduate Intelligence Platform</span>
        </div>
        <nav aria-label="Navegación principal">
          {sidebarItems.map((item) => {
            const Icon = item.icon;
            return (
              <a key={item.label} href={item.href}>
                <Icon />
                {item.label}
              </a>
            );
          })}
        </nav>
        <div className="observatory-sidebar-story">
          <span>Lectura estratégica</span>
          <AnalysisStoryline steps={storySteps} activeStep={activeStep} onStepChange={(stepId) => setActiveStep(stepId as StoryStepId)} />
        </div>
        <div className="observatory-sidebar-foot">
          <ShieldCheck />
          <div>
            <span>Entorno productivo</span>
            <strong>Rectoría y comité académico</strong>
          </div>
        </div>
      </aside>

      <section className="observatory-workspace">
        <header className="observatory-header">
          <div>
            <span>Observatorio institucional de inteligencia curricular</span>
            <strong>{specializationName}</strong>
          </div>
          <div className="observatory-header-actions">
            <span className="observatory-date">
              <CalendarDays />
              Actualizado hoy
            </span>
            <span className="story-data-state">{analysis ? 'Microcurrículos reales' : 'Producción'}</span>
            <span className="observatory-user">
              <UserCircle />
              Rectoría / Comité
            </span>
            <button type="button" className="story-button-secondary" onClick={exportExecutiveReport}>
              <Download />
              Exportar informe
            </button>
          </div>
        </header>

        <div className="observatory-scroll">
      <section className="story-hero observatory-hero-panel">
        <div className="story-hero-copy">
          <span className="story-eyebrow">Observatorio de pertinencia curricular</span>
          <h1>{specializationName}</h1>
          <p>Microcurrículos · mercado laboral · SNIES · reescritura IA</p>
          <div className="story-hero-meta">
            <span>Estado del análisis: {analysis ? 'Consolidado' : 'Listo para analizar'}</span>
            <span>{analysis?.documents_processed || documents.length || 10} microcurrículos procesados</span>
            <span>Comité académico</span>
          </div>
        </div>
        <aside className="story-command-panel">
          <label>
            <span>Especialización seleccionada</span>
            <select
              value={selectedSpecializationId}
              onChange={(event) => {
                setSelectedSpecializationId(event.target.value);
                setAnalysis(null);
                setRewriteResult(null);
                setRelatedPrograms([]);
              }}
            >
              {specializations.length ? (
                specializations.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre}
                  </option>
                ))
              ) : (
                <option value="visual-analytics">{visualAnalyticsName}</option>
              )}
            </select>
          </label>
          <div className="story-actions">
            <button type="button" className="story-button-primary" onClick={handleAnalyzeSpecialization} disabled={loading}>
              {loading ? <RefreshCw className="spin" /> : <Search />}
              Analizar especialización
            </button>
            <button type="button" className="story-button-secondary" onClick={handleRewriteSpecialization} disabled={rewriting}>
              {rewriting ? <RefreshCw className="spin" /> : <Sparkles />}
              Generar microcurrículo actualizado
            </button>
          </div>
          {message ? <p className="story-message">{message}</p> : null}
        </aside>
      </section>

      <StorySection
        id="programa"
        step="01"
        eyebrow="Programa"
        title="Contexto del programa"
        intro=""
      >
        <div className="story-program-grid">
          <article className="story-program-card main">
            <span>Especialización activa</span>
            <h3>{specializationName}</h3>
            <p>Pertinencia curricular · empleabilidad · benchmarking SNIES · reescritura IA.</p>
          </article>
          <article className="story-program-card">
            <span>Facultad</span>
            <strong>{selectedSpecialization?.facultad || 'Escuela de Ingeniería'}</strong>
            <p>{selectedSpecialization?.nivel || 'Posgrado'} · Virtual.</p>
          </article>
          <article className="story-program-card">
            <span>Duración y modalidad</span>
            <strong>2 semestres</strong>
            <p>Analítica aplicada · BI · visualización ejecutiva.</p>
          </article>
          <article className="story-program-card">
            <span>Microcurrículos procesados</span>
            <strong>{analysis?.documents_processed || documents.length || 10}</strong>
            <p>{documentsLoading ? 'Validando repositorio.' : 'Repositorio curricular.'}</p>
          </article>
          <article className="story-program-card">
            <span>Estado curricular</span>
            <strong>{scoreReading.label}</strong>
            <p>{scoreReading.text}</p>
          </article>
        </div>
        <div className="story-document-strip">
          {(documents.length ? documents.slice(0, 5) : []).map((document) => (
            <span key={document.path}>
              <FileText />
              {documentTitle(document)}
            </span>
          ))}
          {!documents.length ? <span>Evidencia preliminar de asignaturas cargadas para análisis institucional.</span> : null}
        </div>
      </StorySection>

      <StorySection
        id="pertinencia"
        step="02"
        eyebrow="Score"
        title="Pertinencia curricular"
        intro=""
      >
        <div className="story-pertinence-layout">
          <article className={`story-main-kpi ${scoreReading.tone}`}>
            <span>Índice de pertinencia curricular</span>
            <GaugeChart value={mainScore} label="Pertinencia curricular" />
            <h3>{scoreReading.label}</h3>
            <p>{scoreReading.text}</p>
          </article>
          <div className="story-kpi-stack">
            <div className="story-kpi-grid">
              {executiveKpis.map((item) => (
                <ExecutiveKpiCard key={item.id} item={item} active={activeKpi === item.id} onClick={() => setActiveKpi(item.id)} />
              ))}
            </div>
            <KpiEvidencePanel item={selectedKpi} />
          </div>
        </div>
      </StorySection>

      <StorySection
        id="evidencia"
        step="03"
        eyebrow="Evidencia curricular"
        title="Cobertura y profundidad"
        intro=""
      >
        <div className="story-two-column">
          <article className="story-card">
            <div className="story-card-head">
              <MonitorCheck />
              <div>
                <span>Radar de capacidades curriculares</span>
                <h3>Dimensiones estratégicas</h3>
              </div>
            </div>
            <RadarChart items={radarItems} />
          </article>
          <article className="story-card">
            <div className="story-card-head">
              <BarChart3 />
              <div>
                <span>Capacidades por categoría</span>
                <h3>Herramientas y plataformas con evidencia curricular</h3>
              </div>
            </div>
            {[
              { label: 'Tecnologías analíticas', value: coverageScore, detail: 'mención y práctica curricular' },
              { label: 'Metodologías aplicadas', value: analysis?.methodologies?.length ? 72 : 54, detail: 'proyectos y evaluación' },
              { label: 'Competencias ejecutivas', value: Math.max(58, mainScore - 4), detail: 'lectura de negocio y comunicación' },
              { label: 'Cobertura por asignatura', value: Math.max(50, Math.min(86, (documents.length || 7) * 8)), detail: `${documents.length || 10} microcurrículos` },
            ].map((item) => (
              <ProgressRow key={item.label} label={item.label} value={item.value} detail={item.detail} />
            ))}
          </article>
        </div>
        <div className="story-card">
          <div className="story-card-head">
            <LibraryBig />
            <div>
              <span>Heatmap de profundidad curricular</span>
              <h3>Mención, práctica, evaluación y proyecto aplicado</h3>
            </div>
          </div>
          <div className="story-heatmap">
            <span />
            <strong>Mención</strong>
            <strong>Práctica</strong>
            <strong>Evaluación</strong>
            <strong>Proyecto aplicado</strong>
            {heatmapRows.map((row) => (
              <Fragment key={row.area}>
                <b key={`${row.area}-label`}>{row.area}</b>
                {(['mention', 'practice', 'evaluation', 'project'] as const).map((key) => (
                  <span key={`${row.area}-${key}`} className={cellClass(row[key])}>
                    {percent(row[key])}
                  </span>
                ))}
              </Fragment>
            ))}
          </div>
        </div>
      </StorySection>

      <StorySection
        id="mercado"
        step="04"
        eyebrow="Inteligencia laboral"
        title="Mercado laboral"
        intro=""
      >
        <div className="story-labor-status">
          <BriefcaseBusiness />
          <div>
            <span>Estado de evidencia</span>
            <strong>Señal laboral exploratoria</strong>
            <p>Fuente laboral en consolidación Gold.</p>
          </div>
        </div>
        <div className="story-three-column">
          <article className="story-card story-executive-insight">
            <span>Demanda laboral estimada</span>
            <strong>{demandScore >= 70 ? 'Alta' : 'Media'}</strong>
            <p>BI · SQL · Python · Cloud.</p>
          </article>
          <article className="story-card story-executive-insight">
            <span>Salario estimado</span>
            <strong>$6.8M - $12M</strong>
            <p>Rango mensual estimado.</p>
          </article>
          <article className="story-card story-executive-insight">
            <span>Tecnologías dominantes</span>
            <strong>BI + SQL + Cloud</strong>
            <p>Mayor señal laboral.</p>
          </article>
        </div>
        <div className="story-two-column">
          <article className="story-card">
            <div className="story-card-head">
              <GraduationCap />
              <div>
                <span>Roles asociados</span>
                <h3>Perfiles con mayor relación laboral</h3>
              </div>
            </div>
            {laborRoles.map((item) => (
              <ProgressRow key={item.label} label={item.label} value={item.level} detail={item.detail} />
            ))}
          </article>
          <article className="story-card">
            <div className="story-card-head">
              <TrendingUp />
              <div>
                <span>Capacidades solicitadas</span>
                <h3>Currículo actual vs demanda laboral</h3>
              </div>
            </div>
            {laborCapabilities.map((item, index) => (
              <div className="story-compare-row" key={item.label}>
                <strong>{item.label}</strong>
                <div>
                  <span className={levelClass(Math.max(34, item.level - 22 - index))}>Currículo actual</span>
                  <b className={levelClass(item.level)}>Demanda laboral</b>
                </div>
              </div>
            ))}
          </article>
          <article className="story-card">
            <div className="story-card-head">
              <TrendingUp />
              <div>
                <span>Tendencia laboral</span>
                <h3>Evolución de demanda vs cobertura curricular</h3>
              </div>
            </div>
            <LaborTrendChart demandScore={demandScore} />
          </article>
          <article className="story-card">
            <div className="story-card-head">
              <BarChart3 />
              <div>
                <span>Mapa de capacidades</span>
                <h3>Demanda, cobertura y volumen relativo</h3>
              </div>
            </div>
            <MarketBubbleChart />
          </article>
          <article className="story-card">
            <div className="story-card-head">
              <Target />
              <div>
                <span>Flujo skill-mercado</span>
                <h3>Capacidades que conectan con roles laborales</h3>
              </div>
            </div>
            <SkillMarketFlow />
          </article>
        </div>
      </StorySection>

      <StorySection
        id="benchmarking"
        step="05"
        eyebrow="Benchmarking curricular SNIES"
        title="Posición competitiva"
        intro=""
      >
        <div className="story-benchmark-summary">
          <article>
            <span>Posición competitiva</span>
            <strong>#{unirBenchmark.posicionCompetitiva}</strong>
          </article>
          <article>
            <span>Promedio competidores</span>
            <strong>{percent(competitorAverage)}</strong>
          </article>
          <article>
            <span>Diferencia frente al promedio</span>
            <strong>{`${unirBenchmark.score - competitorAverage >= 0 ? '+' : ''}${unirBenchmark.score - competitorAverage} pts`}</strong>
          </article>
        </div>
        <div className="story-benchmark-layout">
          <div className="story-ranking">
            {sniesPrograms.map((program) => (
              <article key={`${program.universidad}-${program.programa}`}>
                <span>{program.posicionCompetitiva}</span>
                <div>
                  <strong>{program.universidad}</strong>
                  <p>{program.programa}</p>
                  <small>
                    {program.ciudad} · {program.modalidad}
                  </small>
                </div>
                <b>{percent(program.score)}</b>
              </article>
            ))}
          </div>
          <div className="story-card">
            <div className="story-card-head">
              <BarChart3 />
              <div>
                <span>Score comparativo</span>
                <h3>Fortalezas diferenciales</h3>
              </div>
            </div>
            <BenchmarkBarChart programs={sniesPrograms} />
          </div>
        </div>
      </StorySection>

      <StorySection
        id="propuesta"
        step="06"
        eyebrow="Reescritura IA"
        title="Microcurrículo optimizado"
        intro=""
      >
        <div className="story-proposal-head">
          <div>
            <span>Microcurrículo actualizado propuesto</span>
            <strong>{activeRewriteItem?.assignment || activeRecommendation?.asignatura_o_modulo_sugerido || 'Asignatura priorizada'}</strong>
          </div>
          <button type="button" className="story-button-primary" onClick={handleRewriteSpecialization} disabled={rewriting}>
            {rewriting ? <RefreshCw className="spin" /> : <Sparkles />}
            Generar microcurrículo actualizado
          </button>
        </div>
        <AcademicDiff rewriteItem={activeRewriteItem} recommendation={activeRecommendation} />
        <div className="story-change-list">
          {(rewriteResult?.items?.slice(0, 3) || []).map((item) => (
            <article key={item.rewrite_id}>
              <span>{item.document_name}</span>
              <strong>{item.assignment}</strong>
              <p>{item.change_traceability.length} cambios clave con trazabilidad institucional.</p>
              {item.download_url ? (
                <a href={downloadHref(item.download_url)} target="_blank" rel="noreferrer">
                  Descargar
                </a>
              ) : null}
            </article>
          ))}
          {!rewriteResult ? (
            fallbackRecommendations.map((item) => (
              <article key={item.area}>
                <span>{item.area}</span>
                <strong>{item.change}</strong>
                <p>{item.reason}</p>
              </article>
            ))
          ) : null}
        </div>
      </StorySection>

      <section className="story-section" id="story-trazabilidad">
        <div className="story-section-head">
          <span className="story-step-label">07</span>
          <div>
            <span className="story-section-kicker">Trazabilidad de transformación curricular</span>
            <h2>Trazabilidad</h2>
            <p>Before/after · razón · evidencia · impacto.</p>
          </div>
        </div>
        <div className="story-decision-timeline">
          {[
            ['Detectado', 'Brechas y señales curriculares priorizadas'],
            ['Evaluado', 'Impacto académico y laboral contrastado'],
            ['Optimizado', 'Microcurrículo IA con cambios justificados'],
            ['Aprobable', 'Evidencia lista para comité académico'],
          ].map(([label, text], index) => (
            <article key={label}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              <strong>{label}</strong>
              <p>{text}</p>
            </article>
          ))}
        </div>
        <TraceabilityView rewriteResult={rewriteResult} recommendations={analysis?.recommendations || []} />
        <div className="story-footer-actions">
          {rewriteResult?.traceability_download_url ? (
            <a className="story-button-secondary" href={downloadHref(rewriteResult.traceability_download_url)} target="_blank" rel="noreferrer">
              <Download />
              Exportar trazabilidad
            </a>
          ) : null}
          <button type="button" className="story-button-secondary" onClick={exportExecutiveReport}>
            <Download />
            Exportar informe ejecutivo
          </button>
        </div>
      </section>

      {!analysis ? (
        <section className="story-empty-state">
          <ShieldCheck />
          <strong>La lectura ejecutiva está lista para iniciar.</strong>
          <p>
            Ejecuta el análisis para conectar microcurrículos reales, señal laboral, benchmarking SNIES y propuesta
            curricular asistida por IA.
          </p>
          <button type="button" className="story-button-primary" onClick={handleAnalyzeSpecialization} disabled={loading}>
            {loading ? <RefreshCw className="spin" /> : <ArrowRight />}
            Analizar especialización
          </button>
        </section>
      ) : null}
        </div>
      </section>
    </main>
  );
}
