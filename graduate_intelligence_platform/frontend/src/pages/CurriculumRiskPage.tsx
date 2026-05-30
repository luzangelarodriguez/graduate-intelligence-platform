import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  TrendingDown,
  Target,
  Zap,
  ArrowRight,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts';

import {
  InsightCard,
  NarrativeSection,
  StoryMetric,
  RiskBadge,
  NarrativeSkeleton,
} from '../components/narrative/NarrativeComponents';
import {
  getPrograms,
  getCurriculumGaps,
} from '../services/api';
import type {
  Program,
  CurriculumGap,
} from '../types/api';

interface RiskData {
  programs: Program[];
  gaps: CurriculumGap[];
}

export default function CurriculumRiskPage() {
  const [data, setData] = useState<RiskData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProgram, setSelectedProgram] = useState<Program | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [programsRes, gapsRes] = await Promise.allSettled([
        getPrograms({ limit: 100 }),
        getCurriculumGaps({ limit: 200 }),
      ]);

      setData({
        programs: programsRes.status === 'fulfilled' ? programsRes.value.items : [],
        gaps: gapsRes.status === 'fulfilled' ? gapsRes.value.items : [],
      });
    } catch (err) {
      setError('Error al cargar datos de riesgos curriculares.');
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

  const { programs, gaps } = data;

  // Calculate risk metrics
  const programsAtRisk = programs.filter(p => (p.promedio_match_mercado || 0) < 50);
  const criticalPrograms = programs.filter(p => (p.promedio_match_mercado || 0) < 30);
  const totalGaps = gaps.length;
  const highSeverityGaps = gaps.filter(g => g.gap_severity >= 0.7);
  
  // Group gaps by program
  const gapsByProgram = gaps.reduce((acc, gap) => {
    const spec = gap.specialization || 'Sin programa';
    if (!acc[spec]) acc[spec] = [];
    acc[spec].push(gap);
    return acc;
  }, {} as Record<string, CurriculumGap[]>);

  // Programs ranked by risk (lower alignment = higher risk)
  const rankedPrograms = [...programs]
    .sort((a, b) => (a.promedio_match_mercado || 0) - (b.promedio_match_mercado || 0))
    .slice(0, 10);

  // Calculate potential improvement
  const calculatePotentialImprovement = (program: Program) => {
    const currentAlignment = program.promedio_match_mercado || 0;
    const programGaps = gapsByProgram[program.nombre_especializacion || ''] || [];
    const avgGapSeverity = programGaps.length > 0
      ? programGaps.reduce((sum, g) => sum + g.gap_severity, 0) / programGaps.length
      : 0;
    const potentialIncrease = Math.min(30, Math.round(avgGapSeverity * 20));
    return {
      current: currentAlignment,
      potential: Math.min(100, currentAlignment + potentialIncrease),
      increase: potentialIncrease,
      gapsCount: programGaps.length,
    };
  };

  // Generate narrative
  const generateInsight = () => {
    if (criticalPrograms.length > 0) {
      return `Alerta: ${criticalPrograms.length} programa${criticalPrograms.length !== 1 ? 's' : ''} presenta${criticalPrograms.length === 1 ? '' : 'n'} alineacion critica (<30%). Se requiere revision urgente del curriculo para evitar obsolescencia.`;
    } else if (programsAtRisk.length > 0) {
      return `${programsAtRisk.length} programa${programsAtRisk.length !== 1 ? 's' : ''} muestra${programsAtRisk.length === 1 ? '' : 'n'} riesgo moderado de desalineacion con el mercado. Se identificaron ${totalGaps} brechas de competencias.`;
    }
    return `Los programas muestran buena alineacion general. Se monitorean ${totalGaps} oportunidades de mejora curricular.`;
  };

  // Risk ranking chart data
  const riskChartData = rankedPrograms.map(p => ({
    name: (p.nombre_especializacion || 'Programa').substring(0, 25),
    alignment: p.promedio_match_mercado || 0,
    risk: 100 - (p.promedio_match_mercado || 0),
  }));

  // Gap severity distribution
  const gapSeverityData = [
    { subject: 'Alta Severidad', value: gaps.filter(g => g.gap_severity >= 0.7).length, fullMark: totalGaps },
    { subject: 'Media Severidad', value: gaps.filter(g => g.gap_severity >= 0.4 && g.gap_severity < 0.7).length, fullMark: totalGaps },
    { subject: 'Baja Severidad', value: gaps.filter(g => g.gap_severity < 0.4).length, fullMark: totalGaps },
  ];

  return (
    <div className="space-y-8">
      {/* Main Insight */}
      <InsightCard
        headline={generateInsight()}
        variant={criticalPrograms.length > 0 ? 'danger' : programsAtRisk.length > 0 ? 'warning' : 'success'}
        metric={{
          value: programsAtRisk.length,
          label: 'Programas en Riesgo',
          trend: programsAtRisk.length > 3 ? 'down' : 'neutral',
        }}
      />

      {/* Risk KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StoryMetric
          icon={<AlertTriangle className="w-5 h-5 text-danger" />}
          value={criticalPrograms.length}
          label="Criticos"
          context="Alineacion < 30%"
        />
        <StoryMetric
          icon={<TrendingDown className="w-5 h-5 text-warning" />}
          value={programsAtRisk.length}
          label="En Riesgo"
          context="Alineacion < 50%"
        />
        <StoryMetric
          icon={<Target className="w-5 h-5 text-primary" />}
          value={totalGaps}
          label="Brechas"
          context="Skills faltantes"
        />
        <StoryMetric
          icon={<Zap className="w-5 h-5 text-danger" />}
          value={highSeverityGaps.length}
          label="Alta Severidad"
          context="Brechas criticas"
        />
      </div>

      {/* Risk Ranking */}
      <NarrativeSection
        title="Ranking de Riesgo Curricular"
        subtitle="Programas ordenados por nivel de alineacion (menor = mayor riesgo)"
      >
        <div className="bg-white rounded-lg border border-line p-5">
          {riskChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={riskChartData} layout="vertical" margin={{ left: 160, right: 20 }}>
                <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} fontSize={12} />
                <YAxis type="category" dataKey="name" fontSize={11} tick={{ fill: '#64748B' }} width={150} />
                <Tooltip formatter={(v: number) => [`${v}%`]} />
                <Bar dataKey="alignment" name="Alineacion" radius={[0, 4, 4, 0]}>
                  {riskChartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.alignment < 30 ? '#DC2626' : entry.alignment < 50 ? '#F59E0B' : entry.alignment < 70 ? '#3B82F6' : '#10B981'} 
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

      {/* Two column: Gap radar + Program details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Gap Severity Radar */}
        <NarrativeSection
          title="Distribucion de Severidad"
          subtitle="Clasificacion de brechas por impacto"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {gapSeverityData.some(d => d.value > 0) ? (
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={gapSeverityData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" fontSize={12} />
                  <PolarRadiusAxis angle={30} domain={[0, Math.max(...gapSeverityData.map(d => d.value))]} />
                  <Radar name="Brechas" dataKey="value" stroke="#003A70" fill="#003A70" fillOpacity={0.5} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-muted py-12">Sin brechas identificadas</p>
            )}
          </div>
        </NarrativeSection>

        {/* Impact Simulation */}
        <NarrativeSection
          title="Simulacion de Impacto"
          subtitle="Mejora potencial al cerrar brechas identificadas"
        >
          <div className="bg-white rounded-lg border border-line divide-y divide-line">
            {rankedPrograms.slice(0, 5).map((program, idx) => {
              const improvement = calculatePotentialImprovement(program);
              return (
                <div 
                  key={idx} 
                  className={`p-4 cursor-pointer hover:bg-subtle/50 transition-colors ${
                    selectedProgram?.nombre_especializacion === program.nombre_especializacion ? 'bg-subtle/50' : ''
                  }`}
                  onClick={() => setSelectedProgram(program)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground truncate">{program.nombre_especializacion}</p>
                      <p className="text-xs text-muted mt-1">{improvement.gapsCount} brechas identificadas</p>
                    </div>
                    <RiskBadge 
                      level={improvement.current < 30 ? 'high' : improvement.current < 50 ? 'medium' : 'low'} 
                    />
                  </div>
                  <div className="flex items-center gap-3 mt-3">
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-foreground">{improvement.current}%</span>
                      <ArrowRight size={16} className="text-muted" />
                      <span className="text-lg font-bold text-success">{improvement.potential}%</span>
                    </div>
                    <span className="text-xs text-success">+{improvement.increase}% potencial</span>
                  </div>
                </div>
              );
            })}
          </div>
        </NarrativeSection>
      </div>

      {/* Gap Details Table */}
      <NarrativeSection
        title="Detalle de Brechas Curriculares"
        subtitle="Competencias faltantes por programa y severidad"
      >
        <div className="bg-white rounded-lg border border-line overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-subtle">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Programa</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Skill Faltante</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Severidad</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Demanda</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Prioridad</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {gaps.slice(0, 15).map((gap, idx) => (
                  <tr key={idx} className="hover:bg-subtle/50">
                    <td className="px-4 py-3 text-sm font-medium text-foreground">
                      {(gap.specialization || 'Sin programa').substring(0, 30)}
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">
                      {gap.gap_skill}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 h-2 bg-subtle rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              gap.gap_severity >= 0.7 ? 'bg-danger' : 
                              gap.gap_severity >= 0.4 ? 'bg-warning' : 'bg-success'
                            }`}
                            style={{ width: `${gap.gap_severity * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted">
                          {Math.round(gap.gap_severity * 100)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center text-sm text-foreground">
                      {Math.round(gap.market_demand * 100)}%
                    </td>
                    <td className="px-4 py-3 text-center">
                      <RiskBadge 
                        level={gap.gap_severity >= 0.7 ? 'high' : gap.gap_severity >= 0.4 ? 'medium' : 'low'}
                        label={gap.gap_severity >= 0.7 ? 'Urgente' : gap.gap_severity >= 0.4 ? 'Media' : 'Baja'}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </NarrativeSection>
    </div>
  );
}
