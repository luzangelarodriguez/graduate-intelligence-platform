import { useMemo } from 'react';
import { BarChart3, Building2, CalendarClock, CircleAlert, GraduationCap, Layers3, LineChart, Sparkles, Target, TrendingUp } from 'lucide-react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { AcademicCopilotPanel, type AcademicCopilotBriefing } from '../components/executive-ai/AcademicCopilotPanel';
import {
  AttentionProgramList,
  FindingsFooter,
  HeaderMetricCard,
  InlineAlert,
  MarketComparisonMatrix,
  NarrativeCard,
  RecommendationStack,
  RiskBadge,
  RiskSegmentBar,
  SectionPanel,
  SignalColumn,
  ScenarioPanel,
  TopLevelEmptyState,
  type AttentionProgram,
  type ComparisonRow,
  type ImpactScenario,
  type RecommendationItem,
  type SignalItem,
} from '../components/executive-summary/ExecutiveSummaryBlocks';
import { useExecutiveAi } from '../hooks/useExecutiveAi';
import { useExecutiveSummaryData } from '../hooks/useExecutiveSummaryData';
import type {
  CompanyIntelligenceItem,
  EmergingSkillSignal,
  ExecutiveObservatoryResponse,
  MarketForecastItem,
  ProgramIntelligenceItem,
  RecommendationV2,
} from '../types/api';

function formatNumber(value: number | null | undefined, fallback = 'N/D') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return fallback;
  }
  return new Intl.NumberFormat('es-CO', { maximumFractionDigits: 1 }).format(Number(value));
}

function formatDate(value?: string | null) {
  if (!value) return 'N/D';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function normalizeText(value: string | undefined | null) {
  return String(value || '')
    .trim()
    .toLowerCase();
}

function uniqueStrings(values: Array<string | undefined | null>) {
  return [...new Set(values.map((value) => String(value || '').trim()).filter(Boolean))];
}

function riskLabel(alignment: number) {
  if (alignment >= 70) return 'Alineado';
  if (alignment >= 50) return 'ObservaciÃ³n';
  return 'CrÃ­tico';
}

function riskTone(alignment: number) {
  if (alignment >= 70) return 'green' as const;
  if (alignment >= 50) return 'amber' as const;
  return 'red' as const;
}

function interpretAlignment(alignment: number) {
  if (alignment >= 70) return 'Portafolio con alineaciÃ³n sÃ³lida';
  if (alignment >= 50) return 'Portafolio con presiÃ³n selectiva de actualizaciÃ³n';
  return 'Portafolio con brechas crÃ­ticas';
}

function interpretRisk(risk: number) {
  if (risk >= 70) return 'Requiere intervenciÃ³n prioritaria';
  if (risk >= 50) return 'Requiere monitoreo ejecutivo';
  return 'Riesgo contenido';
}

function safeArray<T>(value: T[] | undefined | null) {
  return Array.isArray(value) ? value : [];
}

function getMetricValue(metrics: Array<{ metric_name: string; metric_value: number }>, candidates: string[]) {
  const entry = metrics.find((metric) => candidates.some((candidate) => normalizeText(metric.metric_name) === normalizeText(candidate)));
  return entry ? Number(entry.metric_value ?? 0) : null;
}

function buildNarrative({
  executiveNarrative,
  programsAnalyzed,
  highRisk,
  criticalGaps,
  emergingNames,
}: {
  executiveNarrative?: string | null;
  programsAnalyzed: number;
  highRisk: number;
  criticalGaps: string[];
  emergingNames: string[];
}) {
  if (executiveNarrative) return executiveNarrative;
  if (!programsAnalyzed) {
    return 'No hay suficientes programas analizados para generar una narrativa ejecutiva institucional.';
  }

  const gapSummary = criticalGaps.length ? criticalGaps.slice(0, 3).join(', ') : 'las brechas curriculares prioritarias';
  const emergingSummary = emergingNames.length ? emergingNames.slice(0, 3).join(', ') : 'competencias emergentes';

  if (highRisk > 0) {
    return `La instituciÃ³n presenta una alineaciÃ³n curricular moderada con el mercado laboral. Se identifican ${highRisk} programas que requieren atenciÃ³n y ${criticalGaps.length || 0} brechas prioritarias. Las mayores oportunidades de mejora se concentran en ${emergingSummary} y en ${gapSummary}.`;
  }

  return `La instituciÃ³n presenta una alineaciÃ³n curricular favorable con el mercado laboral. El portafolio analizado mantiene control sobre sus riesgos principales, aunque siguen siendo relevantes ${gapSummary} y ${emergingSummary}.`;
}

function buildTopPrograms(programs: ProgramIntelligenceItem[]) {
  return [...programs]
    .sort((a, b) => {
      if (b.risk_score !== a.risk_score) return b.risk_score - a.risk_score;
      return a.alignment_score - b.alignment_score;
    })
    .slice(0, 5);
}

function buildAttentionPrograms(programs: ProgramIntelligenceItem[]): AttentionProgram[] {
  return buildTopPrograms(programs)
    .filter((program) => program.alignment_score < 70)
    .slice(0, 5)
    .map((program) => {
      const primaryGap = safeArray(program.top_gaps)[0] as Record<string, unknown> | undefined;
      const primaryRecommendation = safeArray(program.top_recommendations)[0] as Record<string, unknown> | undefined;
      const mainGapDriver =
        String(primaryGap?.missing_skill || primaryGap?.skill || primaryGap?.technology || '').trim() ||
        String(program.business_justification || '').trim() ||
        'Brecha curricular priorizada';
      const recommendedAction =
        String(primaryRecommendation?.recommendation_reasoning || primaryRecommendation?.recommendation_type || '').trim() ||
        program.recommended_actions[0] ||
        'Actualizar resultados de aprendizaje y cobertura curricular.';

      return {
        programName: program.program_name,
        alignment: Number(program.alignment_score || 0),
        riskLevel: riskLabel(program.alignment_score),
        mainGapDriver,
        recommendedAction,
      };
    });
}

function buildMetrics(programs: ProgramIntelligenceItem[], executiveData: ExecutiveObservatoryResponse | null) {
  const safePrograms = safeArray(programs);
  const alignments = safePrograms.map((item) => Number(item.alignment_score || 0));
  const risks = safePrograms.map((item) => Number(item.risk_score || 0));
  const averageAlignment = alignments.length ? alignments.reduce((total, value) => total + value, 0) / alignments.length : executiveData?.alignment_average || 0;
  const averageRisk = risks.length ? risks.reduce((total, value) => total + value, 0) / risks.length : 0;

  return {
    averageAlignment,
    averageRisk,
    programsAnalyzed: executiveData?.programs_analyzed || safePrograms.length,
    alignedPrograms: safePrograms.filter((item) => Number(item.alignment_score || 0) >= 70).length,
    observationPrograms: safePrograms.filter((item) => Number(item.alignment_score || 0) >= 50 && Number(item.alignment_score || 0) < 70).length,
    criticalPrograms: safePrograms.filter((item) => Number(item.alignment_score || 0) < 50).length,
  };
}

function buildMarketSignals(
  emergingSkills: EmergingSkillSignal[],
  companies: CompanyIntelligenceItem[],
  forecasts: MarketForecastItem[],
  topEmergingSkills: Record<string, unknown>[],
) {
  const sourceEmergingItems = (topEmergingSkills.length ? topEmergingSkills : emergingSkills) as Array<Partial<EmergingSkillSignal> & Record<string, unknown>>;
  const emergingSkillItems: SignalItem[] = sourceEmergingItems.slice(0, 5).map((item) => {
    const skillName = String(item.skill_name || item.skill || '').trim();
    const growthRate = Number(item.growth_rate ?? item.growth_velocity ?? item.market_weight ?? 0);
    return {
      label: skillName || 'Skill emergente',
      value: `${formatNumber(growthRate <= 1 ? growthRate * 100 : growthRate)}%`,
      detail: String(item.reason || 'SeÃ±al emergente desde datos de mercado.'),
      progress: Math.max(4, Math.min(100, growthRate <= 1 ? growthRate * 100 : growthRate)),
      tone: growthRate >= 0.7 ? 'green' : growthRate >= 0.4 ? 'amber' : 'blue',
    };
  });

  const technologyItems: SignalItem[] = forecasts
    .filter((item) => normalizeText(item.entity_type).includes('technology') || normalizeText(item.entity_type).includes('tech'))
    .slice(0, 5)
    .map((item) => ({
      label: item.entity_name,
      value: `${formatNumber(item.growth_velocity <= 1 ? item.growth_velocity * 100 : item.growth_velocity)}%`,
      detail: `${item.market_phase || 'SeÃ±al de forecast'} Â· confianza ${formatNumber(item.forecast_confidence <= 1 ? item.forecast_confidence * 100 : item.forecast_confidence)}%`,
      progress: Math.max(4, Math.min(100, item.growth_velocity <= 1 ? item.growth_velocity * 100 : item.growth_velocity)),
      tone: item.market_phase === 'emerging' ? 'amber' : 'blue',
    }));

  const companyItems: SignalItem[] = companies.slice(0, 5).map((item) => ({
    label: item.company,
    value: `${formatNumber(((item.hiring_velocity ?? 0) <= 1 ? (item.hiring_velocity ?? 0) * 100 : (item.hiring_velocity ?? 0)))}%`,
    detail: [item.dominant_cluster, item.dominant_stack].filter(Boolean).join(' Â· ') || 'Observatorio de empresa',
    progress: Math.max(4, Math.min(100, Number(item.hiring_velocity ?? 0) <= 1 ? Number(item.hiring_velocity ?? 0) * 100 : Number(item.hiring_velocity ?? 0))),
    tone: Number(item.ai_adoption_score || 0) >= 0.7 ? 'green' : 'blue',
  }));

  const forecastItems: SignalItem[] = forecasts.slice(0, 5).map((item) => ({
    label: item.entity_name,
    value: `${item.horizon_months}m`,
    detail: `${item.entity_type} Â· fase ${item.market_phase || 'n/d'}`,
    progress: Math.max(4, Math.min(100, item.growth_velocity <= 1 ? item.growth_velocity * 100 : item.growth_velocity)),
    tone: item.market_phase === 'emerging' ? 'amber' : 'slate',
  }));

  return {
    emergingSkillItems,
    technologyItems,
    companyItems,
    forecastItems,
  };
}

function buildComparisonRows(
  criticalGaps: string[],
  topEmergingSkills: string[],
  forecasts: MarketForecastItem[],
  programs: ProgramIntelligenceItem[],
): ComparisonRow[] {
  const combined = uniqueStrings([
    ...criticalGaps,
    ...topEmergingSkills,
    ...forecasts.slice(0, 5).map((item) => item.entity_name),
  ]).slice(0, 8);

  return combined.map((label) => {
    const forecast = forecasts.find((item) => normalizeText(item.entity_name) === normalizeText(label));
    const appearsInGap = criticalGaps.some((gap) => normalizeText(gap) === normalizeText(label));
    const appearsAsEmerging = topEmergingSkills.some((skill) => normalizeText(skill) === normalizeText(label));
    const appearsInProgramGap = programs.some((program) =>
      safeArray(program.top_gaps).some((gap) => normalizeText(String((gap as Record<string, unknown>).missing_skill || (gap as Record<string, unknown>).skill || '')) === normalizeText(label)),
    );

    const growth = Number(forecast?.growth_velocity || 0);
    const marketDemand = growth
      ? growth <= 1
        ? `${(growth * 100).toFixed(1)}%`
        : `${growth.toFixed(1)}`
      : appearsAsEmerging
        ? 'SeÃ±al emergente'
        : appearsInProgramGap
          ? 'Demanda visible'
          : 'Demanda en monitoreo';

    const curriculumCoverage = appearsInGap || appearsInProgramGap ? 'Cobertura baja' : appearsAsEmerging ? 'Cobertura parcial' : 'Cobertura alta';
    const gapStatus: ComparisonRow['gapStatus'] = appearsInGap || appearsInProgramGap ? 'alto' : appearsAsEmerging ? 'medio' : 'bajo';

    return {
      label,
      marketDemand,
      curriculumCoverage,
      gapStatus,
    };
  });
}

function buildScenario(programs: ProgramIntelligenceItem[], recommendations: RecommendationV2[]): ImpactScenario | null {
  const candidate = [...programs].sort((a, b) => a.alignment_score - b.alignment_score)[0];
  if (!candidate) return null;

  const firstRecommendation = safeArray(candidate.top_recommendations)[0] as Record<string, unknown> | undefined;
  const recommendationIncrease = Number(firstRecommendation?.estimated_alignment_increase || 0);
  if (!recommendationIncrease) return null;

  const projected = Math.min(100, Number(candidate.alignment_score || 0) + recommendationIncrease);
  return {
    currentAlignment: Number(candidate.alignment_score || 0),
    projectedAlignment: projected,
    expectedImprovement: projected - Number(candidate.alignment_score || 0),
    rationale:
      String(firstRecommendation?.recommendation_reasoning || candidate.business_justification || 'La evidencia del observatorio sugiere una mejora directa sobre las brechas priorizadas.') ||
      'La evidencia del observatorio sugiere una mejora directa sobre las brechas priorizadas.',
  };
}

function buildRecommendationCards(
  recommendations: RecommendationV2[],
  programs: ProgramIntelligenceItem[],
): RecommendationItem[] {
  const byProgram = [...programs].sort((a, b) => a.alignment_score - b.alignment_score);
  const sourceRecommendations = recommendations.length ? recommendations : byProgram.flatMap((program) =>
    safeArray(program.top_recommendations).map((item) => ({
      recommendation_type: String((item as Record<string, unknown>).recommendation_type || 'curriculum'),
      target_entity: program.program_name,
      target_company: String((item as Record<string, unknown>).target_company || 'mercado laboral'),
      recommendation_score: Number((item as Record<string, unknown>).recommendation_confidence || 0),
      priority: Number((item as Record<string, unknown>).recommendation_confidence || 0) >= 0.8 ? 'Alta' : 'Media',
      business_justification: String((item as Record<string, unknown>).recommendation_reasoning || program.business_justification || ''),
      expected_impact: `Mejora estimada sobre ${program.program_name}`,
      confidence: Number((item as Record<string, unknown>).recommendation_confidence || 0),
      estimated_alignment_increase: Number((item as Record<string, unknown>).estimated_alignment_increase || 0),
      recommendation_evidence: item as Record<string, unknown>,
      recommendation_reasoning: String((item as Record<string, unknown>).recommendation_reasoning || ''),
    })),
  );

  return sourceRecommendations
    .map((item) => ({
      priority: String(item.priority || (item.recommendation_score >= 0.8 ? 'Alta' : 'Media')),
      affectedProgram: String(item.target_entity || item.target_company || 'Programa institucional'),
      title:
        String(item.recommendation_reasoning || item.business_justification || item.recommendation_type || 'ActualizaciÃ³n prioritaria').trim() ||
        'ActualizaciÃ³n prioritaria',
      academicRationale: String(item.business_justification || item.recommendation_reasoning || 'La evidencia del mercado respalda este ajuste curricular.'),
      marketEvidence:
        String((item.recommendation_evidence as Record<string, unknown>)?.market_signal || (item.recommendation_evidence as Record<string, unknown>)?.target_company || item.target_company || 'Evidencia del observatorio de mercado'),
      expectedImpact:
        String(item.expected_impact || `Aumento esperado de ${formatNumber(item.estimated_alignment_increase)} puntos en alineaciÃ³n.`),
      confidence: Number(item.confidence || item.recommendation_score || 0),
    }))
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3);
}

export function ExecutiveSummaryPage() {
  const { executiveObservatory, programs, programIntelligence, recommendations, emergingSkills, companies, forecasts, isLoading, error, refresh } =
    useExecutiveSummaryData();
  const { executiveNarrative, observatoryAnswer, runQuery, isLoading: executiveAiLoading, error: executiveAiError } = useExecutiveAi(null);

  const metrics = useMemo(() => buildMetrics(programIntelligence, executiveObservatory), [programIntelligence, executiveObservatory]);

  const executiveMetrics = useMemo(() => {
    const metricsRows = executiveObservatory?.metrics || [];
    const jobsProcessed = getMetricValue(metricsRows, ['jobs_processed', 'jobs_analyzed', 'jobs_count', 'total_jobs']);
    const companiesMonitored = uniqueStrings(companies.map((item) => item.company)).length;
    const skillsAnalyzed = uniqueStrings([
      ...emergingSkills.map((item) => item.skill_name || item.skill),
      ...programIntelligence.flatMap((program) => [
        ...safeArray(program.top_gaps).map((gap) => String((gap as Record<string, unknown>).missing_skill || (gap as Record<string, unknown>).skill || '')),
        ...safeArray(program.emerging_technologies).map((gap) => String((gap as Record<string, unknown>).technology || '')),
      ]),
      ...forecasts.map((item) => item.entity_name),
    ]).length;

    return [
      {
        label: 'Oferta acadÃ©mica analizada',
        value: formatNumber(metrics.programsAnalyzed),
        detail: 'Programas con seÃ±ales de pertinencia revisados en la Ãºltima corrida.',
        interpretation: `${metrics.alignedPrograms} alineados Â· ${metrics.observationPrograms} en observaciÃ³n Â· ${metrics.criticalPrograms} crÃ­ticos`,
        badge: metrics.programsAnalyzed ? 'Activo' : 'Sin datos',
        tone: metrics.programsAnalyzed ? ('blue' as const) : ('slate' as const),
      },
      {
        label: 'Nivel de alineaciÃ³n curricular',
        value: `${metrics.averageAlignment.toFixed(1)}%`,
        detail: 'Promedio institucional observado sobre el portafolio evaluado.',
        interpretation: interpretAlignment(metrics.averageAlignment),
        badge: metrics.averageAlignment >= 70 ? 'SÃ³lida' : metrics.averageAlignment >= 50 ? 'Moderada' : 'Baja',
        tone: riskTone(metrics.averageAlignment),
      },
      {
        label: 'Riesgo curricular institucional',
        value: `${metrics.averageRisk.toFixed(1)}%`,
        detail: 'Promedio de riesgo sobre los programas analizados.',
        interpretation: interpretRisk(metrics.averageRisk),
        badge: metrics.averageRisk >= 70 ? 'CrÃ­tico' : metrics.averageRisk >= 50 ? 'ObservaciÃ³n' : 'Contenible',
        tone: riskTone(100 - metrics.averageRisk),
      },
      {
        label: 'Ãšltima actualizaciÃ³n',
        value: formatDate(programIntelligence[0]?.generated_at || forecasts[0]?.last_seen_at || executiveObservatory?.metrics?.[0]?.metric_period || null),
        detail: 'Momento del Ãºltimo cÃ¡lculo institucional disponible en producciÃ³n.',
        interpretation: 'ActualizaciÃ³n ejecutiva',
        badge: 'Tiempo real',
        tone: 'slate' as const,
      },
      {
        label: 'Jobs procesados',
        value: jobsProcessed === null ? 'N/D' : formatNumber(jobsProcessed),
        detail: 'SeÃ±ales laborales agregadas en la capa de observabilidad.',
        interpretation: jobsProcessed === null ? 'MÃ©trica no emitida en esta corrida' : 'Procesamiento validado',
        badge: jobsProcessed === null ? 'Pendiente' : 'Disponible',
        tone: jobsProcessed === null ? ('slate' as const) : ('green' as const),
      },
      {
        label: 'Empresas monitoreadas',
        value: formatNumber(companiesMonitored),
        detail: 'Empresas con inteligencia de mercado activa.',
        interpretation: companiesMonitored ? 'Cobertura empresarial' : 'Sin evidencia consolidada',
        badge: companiesMonitored ? 'Activo' : 'Sin datos',
        tone: companiesMonitored ? ('green' as const) : ('slate' as const),
      },
      {
        label: 'Skills analizadas',
        value: formatNumber(skillsAnalyzed),
        detail: 'Skills, tecnologÃ­as y brechas observadas desde fuentes vivas.',
        interpretation: skillsAnalyzed ? 'Cobertura semÃ¡ntica' : 'Sin seÃ±ales suficientes',
        badge: skillsAnalyzed ? 'Disponible' : 'Sin datos',
        tone: skillsAnalyzed ? ('blue' as const) : ('slate' as const),
      },
    ];
  }, [companies, emergingSkills, executiveObservatory?.metrics, forecasts, metrics, programIntelligence]);

  const narrative = useMemo(
    () =>
      buildNarrative({
        executiveNarrative: executiveObservatory?.executive_narrative || null,
        programsAnalyzed: metrics.programsAnalyzed,
        highRisk: executiveObservatory?.high_risk_programs?.length || metrics.criticalPrograms,
        criticalGaps: uniqueStrings(
          (executiveObservatory?.critical_gaps || [])
            .map((item) => String((item as Record<string, unknown>).missing_skill || (item as Record<string, unknown>).skill || ''))
            .filter(Boolean),
        ),
        emergingNames: uniqueStrings([
          ...((executiveObservatory?.top_emerging_skills || []).map((item) => String((item as Record<string, unknown>).skill_name || ''))),
          ...emergingSkills.map((item) => item.skill_name || item.skill),
        ]),
      }),
    [emergingSkills, executiveObservatory?.critical_gaps, executiveObservatory?.executive_narrative, executiveObservatory?.high_risk_programs, executiveObservatory?.top_emerging_skills, metrics.programsAnalyzed, metrics.criticalPrograms],
  );
  const aiNarrative = executiveNarrative?.narrative?.trim() || executiveObservatory?.executive_narrative || narrative;

  const attentionPrograms = useMemo(() => buildAttentionPrograms(programIntelligence), [programIntelligence]);
  const marketSignals = useMemo(
    () => buildMarketSignals(emergingSkills, companies, forecasts, executiveObservatory?.top_emerging_skills || []),
    [companies, emergingSkills, executiveObservatory?.top_emerging_skills, forecasts],
  );

  const comparisonRows = useMemo(() => {
    const criticalGaps = uniqueStrings(
      (executiveObservatory?.critical_gaps || [])
        .map((item) => String((item as Record<string, unknown>).missing_skill || (item as Record<string, unknown>).skill || ''))
        .filter(Boolean),
    );
    const emergingNames = uniqueStrings([
      ...emergingSkills.map((item) => item.skill_name || item.skill),
      ...forecasts.map((item) => item.entity_name),
    ]);
    return buildComparisonRows(criticalGaps, emergingNames, forecasts, programIntelligence);
  }, [emergingSkills, executiveObservatory?.critical_gaps, forecasts, programIntelligence]);

  const scenario = useMemo(() => buildScenario(programIntelligence, recommendations), [programIntelligence, recommendations]);
  const recommendationCards = useMemo(() => buildRecommendationCards(recommendations, programIntelligence), [programIntelligence, recommendations]);

  const findings = useMemo(() => {
    const criticalPrograms = metrics.criticalPrograms || executiveObservatory?.high_risk_programs?.length || 0;
    const emergingList = uniqueStrings([
      ...emergingSkills.slice(0, 2).map((item) => item.skill_name || item.skill),
      ...forecasts
        .filter((item) => normalizeText(item.market_phase) === 'emerging')
        .slice(0, 2)
        .map((item) => item.entity_name),
    ]);
    const topGapNames = uniqueStrings(
      (executiveObservatory?.critical_gaps || [])
        .slice(0, 2)
        .map((item) => String((item as Record<string, unknown>).missing_skill || ''))
        .filter(Boolean),
    );

    return [
      `${criticalPrograms} programas requieren intervenciÃ³n o seguimiento ejecutivo.`,
      topGapNames.length
        ? `Las brechas mÃ¡s fuertes se concentran en ${topGapNames.join(', ')}.`
        : 'Las brechas curriculares se mantienen visibles en el portafolio analizado.',
      emergingList.length
        ? `El mercado muestra mayor tracciÃ³n en ${emergingList.join(', ')}.`
        : 'El mercado mantiene seÃ±ales emergentes que deben seguirse en la siguiente corrida.',
      scenario
        ? `Las actualizaciones curriculares priorizadas podrÃ­an elevar la alineaciÃ³n institucional desde ${scenario.currentAlignment.toFixed(1)}% hasta ${scenario.projectedAlignment.toFixed(1)}%.`
        : 'Las simulaciones predictivas todavÃ­a no entregan una proyecciÃ³n consolidada.',
    ];
  }, [emergingSkills, executiveObservatory?.critical_gaps, executiveObservatory?.high_risk_programs, forecasts, metrics.criticalPrograms, scenario]);

  const copilotBriefing = useMemo<AcademicCopilotBriefing>(() => {
    const priorityPrograms = [
      ...attentionPrograms.slice(0, 5).map(
        (program) =>
          `${program.programName} â€” alineaciÃ³n ${program.alignment.toFixed(1)}% Â· riesgo ${program.riskLevel} Â· ${program.mainGapDriver}`,
      ),
      ...((executiveObservatory?.high_risk_programs || []) as Array<Record<string, unknown>>).slice(0, 3).map((item) => {
        const name = String(item.program_name || item.program || item.nombre_especializacion || 'Programa prioritario');
        const alignment = Number(item.alignment_score ?? item.alignment ?? 0);
        const risk = String(item.risk_level || item.risk || 'N/D');
        return `${name} â€” alineaciÃ³n ${alignment.toFixed(1)}% Â· riesgo ${risk}`;
      }),
    ];

    const criticalGaps = uniqueStrings([
      ...((executiveObservatory?.critical_gaps || []) as Array<Record<string, unknown>>).slice(0, 6).map((item) =>
        String(item.missing_skill || item.skill || item.canonical_skill || item.gap || ''),
      ),
      ...comparisonRows.slice(0, 4).map((row) => `${row.label} Â· ${row.marketDemand}`),
    ]);

    const recommendedActions = uniqueStrings([
      ...recommendationCards.slice(0, 5).map((item) => `${item.title} â€” ${item.academicRationale}`),
      ...(executiveObservatory?.top_recommendations || []).slice(0, 3).map((item) =>
        String((item as Record<string, unknown>).recommendation_reasoning || (item as Record<string, unknown>).recommendation || ''),
      ),
    ]);

    const expectedImpact = uniqueStrings([
      scenario
        ? `Si se aplican las recomendaciones, la alineaciÃ³n podrÃ­a pasar de ${scenario.currentAlignment.toFixed(1)}% a ${scenario.projectedAlignment.toFixed(1)}%.`
        : 'La simulaciÃ³n todavÃ­a no consolida una proyecciÃ³n completa por horizonte.',
      scenario ? `La mejora esperada equivale a +${scenario.expectedImprovement.toFixed(1)} puntos de alineaciÃ³n.` : 'El impacto curricular se calcularÃ¡ cuando la simulaciÃ³n tenga suficiente evidencia.',
      ...findings.slice(0, 2),
    ]);

    const evidence = uniqueStrings([
      ...((executiveObservatory?.source_tables || []) as string[]),
      ...programIntelligence.slice(0, 4).flatMap((program) => program.source_tables || []),
      ...programIntelligence.slice(0, 4).map((program) => program.program_name),
      ...((executiveObservatory?.top_emerging_skills || []) as Array<Record<string, unknown>>)
        .slice(0, 4)
        .map((item) => String(item.skill_name || item.skill || '')),
      ...marketSignals.emergingSkillItems.slice(0, 2).map((item) => item.label),
      ...marketSignals.technologyItems.slice(0, 2).map((item) => item.label),
      ...marketSignals.companyItems.slice(0, 2).map((item) => item.label),
      ...marketSignals.forecastItems.slice(0, 2).map((item) => `${item.label} Â· ${item.value}`),
    ]);

    return {
      diagnosis: aiNarrative,
      priorityPrograms,
      criticalGaps,
      recommendedActions,
      expectedImpact,
      evidence,
      model: executiveNarrative?.model || (executiveObservatory?.executive_narrative ? 'deterministic-fallback' : undefined),
      fallbackNote:
        executiveNarrative?.model === 'deterministic-fallback'
          ? 'Análisis generado con narrativa determinística. La explicación avanzada se activará cuando el servicio esté disponible.'
          : undefined,
    };
  }, [
    aiNarrative,
    attentionPrograms,
    comparisonRows,
    executiveNarrative?.model,
    executiveObservatory?.critical_gaps,
    executiveObservatory?.executive_narrative,
    executiveObservatory?.high_risk_programs,
    executiveObservatory?.source_tables,
    executiveObservatory?.top_emerging_skills,
    executiveObservatory?.top_recommendations,
    findings,
    marketSignals,
    programIntelligence,
    recommendationCards,
    scenario,
  ]);

  const topEmergingSkillRows = marketSignals.emergingSkillItems;
  const topTechnologiesRows = marketSignals.technologyItems;
  const topCompaniesRows = marketSignals.companyItems;
  const forecastRows = marketSignals.forecastItems;

  if (isLoading) {
    return <LoadingState label="Cargando observatorio ejecutivo institucional..." />;
  }

  if (!executiveObservatory && !programIntelligence.length && !programs.length) {
    return (
      <TopLevelEmptyState
        title="No fue posible construir el Resumen Ejecutivo"
        body="Las fuentes vivas no devolvieron datos suficientes para componer la lectura institucional. Intenta recargar la pÃ¡gina o verifica la conexiÃ³n con la API."
      />
    );
  }

  return (
    <main className="min-h-screen bg-[#F8FAFC] text-[#1E293B]">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-8 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <header className="rounded-[2rem] border border-slate-200 bg-white px-6 py-6 shadow-[0_1px_0_rgba(15,23,42,0.03)]">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full bg-[#EAF2FB] px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-[#003B71]">
                <GraduationCap size={16} />
                Observatorio de Pertinencia AcadÃ©mica
              </div>
              <div className="space-y-2">
                <h1 className="text-3xl font-semibold tracking-tight text-[#1E293B] md:text-4xl">Universidad Internacional de La Rioja - Colombia</h1>
                <p className="max-w-4xl text-sm leading-7 text-[#64748B]">
                  Actualizado con informaciÃ³n del mercado laboral, competencias emergentes y anÃ¡lisis curricular.
                </p>
              </div>
            </div>
            <div className="grid min-w-[280px] gap-2 rounded-2xl border border-slate-200 bg-[#F8FAFC] p-4 text-sm text-[#1E293B]">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[#64748B]">Last update</span>
                <strong>{formatDate(programIntelligence[0]?.generated_at || forecasts[0]?.last_seen_at || executiveObservatory?.metrics?.[0]?.metric_period || null)}</strong>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[#64748B]">Programs analyzed</span>
                <strong>{formatNumber(metrics.programsAnalyzed)}</strong>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[#64748B]">Jobs processed</span>
                <strong>
                  {formatNumber(getMetricValue(executiveObservatory?.metrics || [], ['jobs_processed', 'jobs_analyzed', 'jobs_count', 'total_jobs']))}
                </strong>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[#64748B]">Companies monitored</span>
                <strong>{formatNumber(uniqueStrings(companies.map((item) => item.company)).length)}</strong>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[#64748B]">Skills analyzed</span>
                <strong>
                  {formatNumber(
                    uniqueStrings([
                      ...emergingSkills.map((item) => item.skill_name || item.skill),
                      ...forecasts.map((item) => item.entity_name),
                      ...programIntelligence.flatMap((program) => [
                        ...safeArray(program.top_gaps).map((gap) => String((gap as Record<string, unknown>).missing_skill || (gap as Record<string, unknown>).skill || '')),
                        ...safeArray(program.emerging_technologies).map((gap) => String((gap as Record<string, unknown>).technology || '')),
                      ]),
                    ]).length,
                  )}
                </strong>
              </div>
            </div>
          </div>
        </header>

        {error ? <InlineAlert message={error} /> : null}

        <SectionPanel title="Estado Institucional" subtitle="Lectura ejecutiva construida exclusivamente a partir de datos vivos del observatorio y del mercado laboral.">
          <NarrativeCard title="Narrativa ejecutiva" narrative={aiNarrative} caption="La sÃ­ntesis se recalcula con la Ãºltima informaciÃ³n disponible en producciÃ³n y puede incluir explicaciÃ³n generada por IA." />
        </SectionPanel>

        <AcademicCopilotPanel
          title="AnÃ¡lisis ejecutivo generado por IA"
          subtitle="SÃ­ntesis automÃ¡tica sobre pertinencia acadÃ©mica, brechas curriculares y seÃ±ales de mercado."
          briefing={copilotBriefing}
          briefingLoading={executiveAiLoading}
          loading={executiveAiLoading}
          error={executiveAiError}
          answer={observatoryAnswer}
          onAsk={runQuery}
          suggestedQuestions={[
            'Â¿QuÃ© programas requieren actualizaciÃ³n inmediata?',
            'Â¿QuÃ© competencias faltan en Visual Analytics?',
            'Â¿QuÃ© habilidades estÃ¡n creciendo mÃ¡s rÃ¡pido?',
            'Â¿QuÃ© empresas demandan estas capacidades?',
            'Â¿QuÃ© pasa si agregamos Azure y Databricks?',
          ]}
        />

        <SectionPanel title="Estado institucional resumido" subtitle="Tres indicadores para direcciÃ³n acadÃ©mica y comitÃ© ejecutivo.">
          <div className="grid gap-4 lg:grid-cols-3">
            {executiveMetrics.slice(0, 3).map((metric) => (
              <HeaderMetricCard key={metric.label} {...metric} />
            ))}
          </div>
        </SectionPanel>

        <SectionPanel title="SegmentaciÃ³n del riesgo acadÃ©mico" subtitle="Lectura horizontal del portafolio acadÃ©mico segÃºn alineaciÃ³n detectada.">
          <RiskSegmentBar aligned={metrics.alignedPrograms} observation={metrics.observationPrograms} critical={metrics.criticalPrograms} total={metrics.programsAnalyzed} />
        </SectionPanel>

        <SectionPanel title="Programas que requieren atenciÃ³n" subtitle="Ranking ejecutivo de programas priorizados por riesgo y brecha principal.">
          <AttentionProgramList items={attentionPrograms} />
        </SectionPanel>

        <SectionPanel title="Â¿QuÃ© estÃ¡ pidiendo el mercado?" subtitle="SeÃ±ales vivas del mercado laboral, empresas observadas y tecnologÃ­as en aceleraciÃ³n.">
          <div className="grid gap-4 xl:grid-cols-4">
            <SignalColumn title="Top emerging skills" icon={Sparkles} items={topEmergingSkillRows} emptyMessage="No se registraron skills emergentes con suficiente evidencia." />
            <SignalColumn title="Top technologies" icon={Layers3} items={topTechnologiesRows} emptyMessage="No se consolidaron tecnologÃ­as emergentes suficientes en la corrida." />
            <SignalColumn title="Top companies" icon={Building2} items={topCompaniesRows} emptyMessage="No se consolidaron empresas con observatorio activo en esta ejecuciÃ³n." />
            <SignalColumn title="Labor forecast signals" icon={TrendingUp} items={forecastRows} emptyMessage="No hubo seÃ±ales de forecast suficientes para construir la curva laboral." />
          </div>
        </SectionPanel>

        <SectionPanel title="University vs Market" subtitle="Comparativo de demanda de mercado y cobertura curricular sobre skills o tecnologÃ­as priorizadas.">
          <MarketComparisonMatrix rows={comparisonRows} />
        </SectionPanel>

        <SectionPanel title="Â¿QuÃ© ocurrirÃ­a si actualizamos el currÃ­culo?" subtitle="Escenario de impacto basado Ãºnicamente en cÃ¡lculos predictivos del observatorio.">
          <ScenarioPanel scenario={scenario} />
        </SectionPanel>

        <SectionPanel title="Prioritized Recommendations" subtitle="MÃ¡ximo tres recomendaciones principales, expresadas en lenguaje acadÃ©mico e institucional.">
          <RecommendationStack items={recommendationCards} />
        </SectionPanel>

        <FindingsFooter findings={findings} />
      </div>
    </main>
  );
}




