import { useCallback, useEffect, useState } from 'react';
import {
  GraduationCap,
  Building2,
  Lightbulb,
  AlertTriangle,
  TrendingUp,
  Target,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts';

import {
  InsightCard,
  ExecutiveKpi,
  NarrativeSection,
  RiskBadge,
  StoryMetric,
  NarrativeSkeleton,
} from '../components/narrative/NarrativeComponents';
import {
  getPrograms,
  getCompanyIntelligence,
  getCurriculumGaps,
  getObservatoryRecommendations,
} from '../services/api';
import type {
  Program,
  CompanyIntelligence,
  CurriculumGap,
  ObservatoryRecommendation,
} from '../types/api';

interface DashboardData {
  programs: Program[];
  companies: CompanyIntelligence[];
  gaps: CurriculumGap[];
  recommendations: ObservatoryRecommendation[];
}

export default function ExecutiveSummaryPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [programsRes, companiesRes, gapsRes, recsRes] = await Promise.allSettled([
        getPrograms({ limit: 100 }),
        getCompanyIntelligence({ limit: 100 }),
        getCurriculumGaps({ limit: 100 }),
        getObservatoryRecommendations({ limit: 100 }),
      ]);

      setData({
        programs: programsRes.status === 'fulfilled' ? programsRes.value.items : [],
        companies: companiesRes.status === 'fulfilled' ? companiesRes.value.items : [],
        gaps: gapsRes.status === 'fulfilled' ? gapsRes.value.items : [],
        recommendations: recsRes.status === 'fulfilled' ? recsRes.value.items : [],
      });
    } catch (err) {
      setError('Error al cargar los datos del observatorio.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (isLoading) return <NarrativeSkeleton />;
  if (error) return <div className="text-danger text-center py-12">{error}</div>;
  if (!data) return null;

  // Calculate metrics
  const totalPrograms = data.programs.length;
  const avgAlignment = totalPrograms > 0
    ? Math.round(data.programs.reduce((sum, p) => sum + (p.promedio_match_mercado || 0), 0) / totalPrograms)
    : 0;
  const totalCompanies = data.companies.length;
  const totalGaps = data.gaps.length;
  const totalRecommendations = data.recommendations.length;

  // Programs at risk (alignment < 50%)
  const programsAtRisk = data.programs.filter(p => (p.promedio_match_mercado || 0) < 50);
  const highRiskCount = programsAtRisk.length;

  // Top programs by alignment
  const topPrograms = [...data.programs]
    .sort((a, b) => (b.promedio_match_mercado || 0) - (a.promedio_match_mercado || 0))
    .slice(0, 6);

  // Gap distribution
  const highSeverityGaps = data.gaps.filter(g => g.gap_severity >= 0.7).length;
  const mediumSeverityGaps = data.gaps.filter(g => g.gap_severity >= 0.4 && g.gap_severity < 0.7).length;
  const lowSeverityGaps = data.gaps.filter(g => g.gap_severity < 0.4).length;

  // Recommendations by type
  const recsByType = data.recommendations.reduce((acc, r) => {
    const type = r.recommendation_type || 'other';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Generate narrative headline
  const generateHeadline = () => {
    if (avgAlignment >= 70) {
      return `La alineacion curricular se mantiene solida en ${avgAlignment}%, aunque ${highRiskCount} programa${highRiskCount !== 1 ? 's' : ''} requiere${highRiskCount === 1 ? '' : 'n'} atencion inmediata.`;
    } else if (avgAlignment >= 50) {
      return `La alineacion curricular es moderada (${avgAlignment}%). Se identifican ${totalGaps} brechas de competencias que impactan ${highRiskCount} programa${highRiskCount !== 1 ? 's' : ''}.`;
    } else {
      return `Alerta: La alineacion curricular es critica (${avgAlignment}%). Se requiere accion inmediata en ${highRiskCount} programa${highRiskCount !== 1 ? 's' : ''}.`;
    }
  };

  // Chart data
  const alignmentChartData = topPrograms.map(p => ({
    name: (p.nombre_especializacion || 'Programa').substring(0, 20),
    value: p.promedio_match_mercado || 0,
  }));

  const gapChartData = [
    { name: 'Alta', value: highSeverityGaps, color: '#DC2626' },
    { name: 'Media', value: mediumSeverityGaps, color: '#F59E0B' },
    { name: 'Baja', value: lowSeverityGaps, color: '#10B981' },
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-8">
      {/* Main Insight */}
      <InsightCard
        headline={generateHeadline()}
        variant={avgAlignment >= 70 ? 'success' : avgAlignment >= 50 ? 'warning' : 'danger'}
        metric={{
          value: `${avgAlignment}%`,
          label: 'Alineacion Promedio',
          trend: avgAlignment >= 60 ? 'up' : 'down',
        }}
      />

      {/* Executive KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StoryMetric
          icon={<GraduationCap className="w-5 h-5 text-primary" />}
          value={totalPrograms}
          label="Programas"
          context="Especializaciones analizadas"
        />
        <StoryMetric
          icon={<Target className="w-5 h-5 text-primary" />}
          value={`${avgAlignment}%`}
          label="Alineacion"
          context="Promedio con mercado"
        />
        <StoryMetric
          icon={<Building2 className="w-5 h-5 text-primary" />}
          value={totalCompanies}
          label="Empresas"
          context="Fuentes de demanda"
        />
        <StoryMetric
          icon={<AlertTriangle className="w-5 h-5 text-warning" />}
          value={totalGaps}
          label="Brechas"
          context="Competencias faltantes"
        />
        <StoryMetric
          icon={<Lightbulb className="w-5 h-5 text-primary" />}
          value={totalRecommendations}
          label="Recomendaciones"
          context="Acciones sugeridas"
        />
        <StoryMetric
          icon={<TrendingUp className="w-5 h-5 text-danger" />}
          value={highRiskCount}
          label="En Riesgo"
          context="Programas < 50%"
        />
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Programs by Alignment */}
        <NarrativeSection
          title="Programas por Alineacion"
          subtitle="Top 6 especializaciones segun coincidencia con demanda laboral"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {alignmentChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={alignmentChartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} fontSize={12} />
                  <YAxis type="category" dataKey="name" width={120} fontSize={11} tick={{ fill: '#64748B' }} />
                  <Tooltip formatter={(v: number) => [`${v}%`, 'Alineacion']} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {alignmentChartData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.value >= 70 ? '#10B981' : entry.value >= 50 ? '#F59E0B' : '#DC2626'} 
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-muted py-12">Sin datos de programas</p>
            )}
          </div>
        </NarrativeSection>

        {/* Gap Distribution */}
        <NarrativeSection
          title="Distribucion de Brechas"
          subtitle="Clasificacion por severidad del gap de competencias"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {gapChartData.length > 0 ? (
              <div className="flex items-center gap-8">
                <ResponsiveContainer width="50%" height={200}>
                  <PieChart>
                    <Pie
                      data={gapChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      dataKey="value"
                      labelLine={false}
                    >
                      {gapChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-3">
                  {gapChartData.map((item) => (
                    <div key={item.name} className="flex items-center gap-3">
                      <span 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: item.color }} 
                      />
                      <span className="text-sm text-foreground">{item.name}</span>
                      <span className="text-sm font-bold text-foreground">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-center text-muted py-12">Sin brechas identificadas</p>
            )}
          </div>
        </NarrativeSection>
      </div>

      {/* Programs at Risk */}
      {programsAtRisk.length > 0 && (
        <NarrativeSection
          title="Programas que Requieren Atencion"
          subtitle="Especializaciones con alineacion inferior al 50%"
        >
          <div className="bg-white rounded-lg border border-line divide-y divide-line">
            {programsAtRisk.slice(0, 5).map((program, idx) => (
              <div key={idx} className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">{program.nombre_especializacion}</p>
                  <p className="text-sm text-muted">{program.rol || 'Sin rol'}</p>
                </div>
                <div className="flex items-center gap-4">
                  <RiskBadge level={(program.promedio_match_mercado || 0) < 30 ? 'high' : 'medium'} />
                  <span className="text-lg font-bold text-foreground">
                    {program.promedio_match_mercado || 0}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </NarrativeSection>
      )}

      {/* Key Recommendations */}
      <NarrativeSection
        title="Recomendaciones Prioritarias"
        subtitle="Acciones de mayor impacto identificadas por el sistema"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.recommendations.slice(0, 6).map((rec, idx) => {
            const confidence = rec.recommendation_confidence 
              ? Math.round(parseFloat(rec.recommendation_confidence) * 100) 
              : null;
            return (
              <div key={idx} className="bg-white rounded-lg border border-line p-5">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <span className="text-xs font-medium text-primary uppercase">
                    {rec.recommendation_type}
                  </span>
                  {confidence && (
                    <span className="text-xs text-muted">{confidence}% confianza</span>
                  )}
                </div>
                <p className="text-sm font-medium text-foreground">
                  {rec.target_role || rec.recommendation_type}
                </p>
                {rec.recommendation_reasoning && (
                  <p className="text-xs text-muted mt-2 line-clamp-2">
                    {rec.recommendation_reasoning}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </NarrativeSection>
    </div>
  );
}
