import { useCallback, useEffect, useState } from 'react';
import {
  Users,
  FileText,
  TrendingUp,
  Target,
  Download,
  ArrowRight,
  CheckCircle,
  AlertTriangle,
  BarChart3,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
} from 'recharts';

import {
  InsightCard,
  NarrativeSection,
  StoryMetric,
  EvidenceCard,
  RiskBadge,
  NarrativeSkeleton,
} from '../components/narrative/NarrativeComponents';
import {
  getPrograms,
  getCurriculumGaps,
  getObservatoryRecommendations,
  getCompanyIntelligence,
  getObservatoryHealth,
} from '../services/api';
import type {
  Program,
  CurriculumGap,
  ObservatoryRecommendation,
  CompanyIntelligence,
  HealthResponse,
} from '../types/api';

interface CommitteeData {
  programs: Program[];
  gaps: CurriculumGap[];
  recommendations: ObservatoryRecommendation[];
  companies: CompanyIntelligence[];
  health: HealthResponse | null;
}

export default function AcademicCommitteePage() {
  const [data, setData] = useState<CommitteeData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProgram, setSelectedProgram] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [programsRes, gapsRes, recsRes, companiesRes, healthRes] = await Promise.allSettled([
        getPrograms({ limit: 100 }),
        getCurriculumGaps({ limit: 200 }),
        getObservatoryRecommendations({ limit: 100 }),
        getCompanyIntelligence({ limit: 100 }),
        getObservatoryHealth(),
      ]);

      setData({
        programs: programsRes.status === 'fulfilled' ? programsRes.value.items : [],
        gaps: gapsRes.status === 'fulfilled' ? gapsRes.value.items : [],
        recommendations: recsRes.status === 'fulfilled' ? recsRes.value.items : [],
        companies: companiesRes.status === 'fulfilled' ? companiesRes.value.items : [],
        health: healthRes.status === 'fulfilled' ? healthRes.value : null,
      });
    } catch (err) {
      setError('Error al cargar datos para el comite academico.');
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

  const { programs, gaps, recommendations, companies, health } = data;

  // Calculate metrics
  const avgAlignment = programs.length > 0
    ? Math.round(programs.reduce((sum, p) => sum + (p.promedio_match_mercado || 0), 0) / programs.length)
    : 0;
  const programsAtRisk = programs.filter(p => (p.promedio_match_mercado || 0) < 50);
  const highPriorityRecs = recommendations.filter(r => {
    const conf = r.recommendation_confidence ? parseFloat(r.recommendation_confidence) : (r.confidence || 0);
    return conf >= 0.7;
  });

  // Programs with gaps
  const programsWithGaps = new Set(gaps.map(g => g.specialization)).size;

  // Generate executive summary
  const generateSummary = () => {
    const parts: string[] = [];
    parts.push(`El observatorio analizo ${programs.length} programas academicos.`);
    parts.push(`La alineacion promedio con el mercado es del ${avgAlignment}%.`);
    if (programsAtRisk.length > 0) {
      parts.push(`${programsAtRisk.length} programa${programsAtRisk.length !== 1 ? 's' : ''} requiere${programsAtRisk.length === 1 ? '' : 'n'} atencion prioritaria.`);
    }
    parts.push(`Se generaron ${highPriorityRecs.length} recomendaciones de alta prioridad.`);
    return parts.join(' ');
  };

  // Programs for decision matrix
  const decisionMatrix = programs
    .map(p => ({
      name: p.nombre_especializacion || 'Programa',
      alignment: p.promedio_match_mercado || 0,
      gapsCount: gaps.filter(g => g.specialization === p.nombre_especializacion).length,
      recsCount: recommendations.filter(r => 
        r.target_role?.includes(p.nombre_especializacion || '') || 
        r.recommendation_reasoning?.includes(p.nombre_especializacion || '')
      ).length,
    }))
    .sort((a, b) => a.alignment - b.alignment)
    .slice(0, 10);

  // Alignment distribution data
  const alignmentDistribution = [
    { range: '0-30%', count: programs.filter(p => (p.promedio_match_mercado || 0) < 30).length, color: '#DC2626' },
    { range: '30-50%', count: programs.filter(p => (p.promedio_match_mercado || 0) >= 30 && (p.promedio_match_mercado || 0) < 50).length, color: '#F59E0B' },
    { range: '50-70%', count: programs.filter(p => (p.promedio_match_mercado || 0) >= 50 && (p.promedio_match_mercado || 0) < 70).length, color: '#3B82F6' },
    { range: '70-100%', count: programs.filter(p => (p.promedio_match_mercado || 0) >= 70).length, color: '#10B981' },
  ];

  // Selected program details
  const selectedProgramData = selectedProgram 
    ? programs.find(p => p.nombre_especializacion === selectedProgram) 
    : null;
  const selectedProgramGaps = selectedProgram 
    ? gaps.filter(g => g.specialization === selectedProgram) 
    : [];

  return (
    <div className="space-y-8">
      {/* Executive Summary */}
      <InsightCard
        headline={generateSummary()}
        body="Este informe consolida evidencia del mercado laboral para facilitar decisiones del comite academico."
        variant={avgAlignment >= 60 ? 'success' : avgAlignment >= 40 ? 'warning' : 'danger'}
        metric={{
          value: `${avgAlignment}%`,
          label: 'Alineacion General',
          trend: avgAlignment >= 60 ? 'up' : 'down',
        }}
      />

      {/* Committee Dashboard KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StoryMetric
          icon={<FileText className="w-5 h-5 text-primary" />}
          value={programs.length}
          label="Programas"
          context="Analizados"
        />
        <StoryMetric
          icon={<Target className="w-5 h-5 text-primary" />}
          value={`${avgAlignment}%`}
          label="Alineacion"
          context="Promedio"
        />
        <StoryMetric
          icon={<AlertTriangle className="w-5 h-5 text-warning" />}
          value={programsAtRisk.length}
          label="En Riesgo"
          context="< 50%"
        />
        <StoryMetric
          icon={<BarChart3 className="w-5 h-5 text-primary" />}
          value={gaps.length}
          label="Brechas"
          context="Identificadas"
        />
        <StoryMetric
          icon={<TrendingUp className="w-5 h-5 text-success" />}
          value={highPriorityRecs.length}
          label="Prioritarias"
          context="Recomendaciones"
        />
        <StoryMetric
          icon={<Users className="w-5 h-5 text-primary" />}
          value={companies.length}
          label="Empresas"
          context="Fuentes de datos"
        />
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Alignment Distribution */}
        <NarrativeSection
          title="Distribucion de Alineacion"
          subtitle="Clasificacion de programas por rango de alineacion"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={alignmentDistribution}>
                <XAxis dataKey="range" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" name="Programas" radius={[4, 4, 0, 0]}>
                  {alignmentDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </NarrativeSection>

        {/* System Status */}
        <NarrativeSection
          title="Estado del Sistema"
          subtitle="Verificacion de fuentes de datos y ultima actualizacion"
        >
          <div className="bg-white rounded-lg border border-line p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Estado general</span>
              <span className={`flex items-center gap-2 text-sm font-medium ${
                health?.status === 'healthy' ? 'text-success' : 'text-warning'
              }`}>
                <CheckCircle size={16} />
                {health?.status === 'healthy' ? 'Operativo' : 'Limitado'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Base de datos</span>
              <span className={`text-sm font-medium ${
                health?.database === 'connected' ? 'text-success' : 'text-danger'
              }`}>
                {health?.database === 'connected' ? 'Conectada' : 'Desconectada'}
              </span>
            </div>
            {health?.observatory_freshness && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Registros procesados</span>
                  <span className="text-sm font-medium text-foreground">
                    {health.observatory_freshness.records_count?.toLocaleString() || 'N/A'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Ultima actualizacion</span>
                  <span className="text-sm text-muted">
                    {health.observatory_freshness.last_update 
                      ? new Date(health.observatory_freshness.last_update).toLocaleDateString('es-CO')
                      : 'N/A'}
                  </span>
                </div>
              </>
            )}
          </div>
        </NarrativeSection>
      </div>

      {/* Decision Matrix */}
      <NarrativeSection
        title="Matriz de Decision"
        subtitle="Programas ordenados por prioridad de intervencion"
      >
        <div className="bg-white rounded-lg border border-line overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-subtle">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Programa</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Alineacion</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Brechas</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Prioridad</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Accion</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {decisionMatrix.map((item, idx) => (
                  <tr 
                    key={idx} 
                    className={`hover:bg-subtle/50 cursor-pointer ${
                      selectedProgram === item.name ? 'bg-primary/5' : ''
                    }`}
                    onClick={() => setSelectedProgram(
                      selectedProgram === item.name ? null : item.name
                    )}
                  >
                    <td className="px-4 py-3 text-sm font-medium text-foreground">
                      {item.name.substring(0, 40)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 h-2 bg-subtle rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              item.alignment >= 70 ? 'bg-success' : 
                              item.alignment >= 50 ? 'bg-primary' : 
                              item.alignment >= 30 ? 'bg-warning' : 'bg-danger'
                            }`}
                            style={{ width: `${item.alignment}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-foreground w-10">
                          {item.alignment}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center text-sm text-foreground">
                      {item.gapsCount}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <RiskBadge 
                        level={item.alignment < 30 ? 'high' : item.alignment < 50 ? 'medium' : 'low'}
                        label={item.alignment < 30 ? 'Critica' : item.alignment < 50 ? 'Alta' : 'Normal'}
                      />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button className="text-primary hover:text-primary/80 text-sm font-medium flex items-center gap-1 mx-auto">
                        Ver detalle
                        <ArrowRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </NarrativeSection>

      {/* Selected Program Detail */}
      {selectedProgramData && (
        <NarrativeSection
          title={`Detalle: ${selectedProgramData.nombre_especializacion}`}
          subtitle="Evidencia y brechas identificadas para decision del comite"
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Program Info */}
            <EvidenceCard
              title="Informacion del Programa"
              source="Observatorio Curricular"
              date={new Date().toLocaleDateString('es-CO')}
            >
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted">Rol:</span>
                  <span className="font-medium">{selectedProgramData.rol || 'No especificado'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Alineacion:</span>
                  <span className={`font-bold ${
                    (selectedProgramData.promedio_match_mercado || 0) >= 70 ? 'text-success' : 
                    (selectedProgramData.promedio_match_mercado || 0) >= 50 ? 'text-primary' : 'text-danger'
                  }`}>
                    {selectedProgramData.promedio_match_mercado || 0}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Skills cubiertas:</span>
                  <span className="font-medium">{selectedProgramData.skills_cubiertas || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Empleos relacionados:</span>
                  <span className="font-medium">{selectedProgramData.total_empleos_relacionados || 0}</span>
                </div>
              </div>
            </EvidenceCard>

            {/* Program Gaps */}
            <EvidenceCard
              title="Brechas Identificadas"
              source="Analisis de Mercado Laboral"
              date={new Date().toLocaleDateString('es-CO')}
            >
              {selectedProgramGaps.length > 0 ? (
                <div className="space-y-2">
                  {selectedProgramGaps.slice(0, 5).map((gap, idx) => (
                    <div key={idx} className="flex items-center justify-between py-1">
                      <span className="text-sm">{gap.gap_skill}</span>
                      <RiskBadge 
                        level={gap.gap_severity >= 0.7 ? 'high' : gap.gap_severity >= 0.4 ? 'medium' : 'low'}
                        label={`${Math.round(gap.gap_severity * 100)}%`}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted text-center py-4">Sin brechas identificadas</p>
              )}
            </EvidenceCard>
          </div>
        </NarrativeSection>
      )}

      {/* Evidence Section */}
      <NarrativeSection
        title="Evidencia de Mercado"
        subtitle="Datos consolidados de empresas y demanda laboral"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <EvidenceCard
            title="Fuentes de Demanda"
            source="Inteligencia Empresarial"
            date={new Date().toLocaleDateString('es-CO')}
          >
            <p className="text-2xl font-bold text-foreground mb-1">{companies.length}</p>
            <p className="text-sm text-muted">empresas analizadas con datos de contratacion y madurez tecnologica.</p>
          </EvidenceCard>

          <EvidenceCard
            title="Brechas de Competencias"
            source="Analisis Curricular"
            date={new Date().toLocaleDateString('es-CO')}
          >
            <p className="text-2xl font-bold text-foreground mb-1">{gaps.length}</p>
            <p className="text-sm text-muted">skills faltantes identificadas en {programsWithGaps} programas academicos.</p>
          </EvidenceCard>

          <EvidenceCard
            title="Recomendaciones IA"
            source="Motor de Recomendaciones"
            date={new Date().toLocaleDateString('es-CO')}
          >
            <p className="text-2xl font-bold text-foreground mb-1">{recommendations.length}</p>
            <p className="text-sm text-muted">acciones sugeridas, {highPriorityRecs.length} de alta prioridad.</p>
          </EvidenceCard>
        </div>
      </NarrativeSection>
    </div>
  );
}
