import { useCallback, useEffect, useState } from 'react';
import {
  Lightbulb,
  Target,
  Clock,
  CheckCircle,
  AlertCircle,
  ArrowUpRight,
  Filter,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
} from 'recharts';

import {
  InsightCard,
  NarrativeSection,
  StoryMetric,
  RiskBadge,
  NarrativeSkeleton,
} from '../components/narrative/NarrativeComponents';
import {
  getObservatoryRecommendations,
} from '../services/api';
import type {
  ObservatoryRecommendation,
} from '../types/api';

type ImpactLevel = 'high' | 'medium' | 'low';
type FilterType = 'all' | 'student' | 'career' | 'curriculum';

export default function RecommendationsCenterPage() {
  const [recommendations, setRecommendations] = useState<ObservatoryRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<FilterType>('all');

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getObservatoryRecommendations({ limit: 100 });
      setRecommendations(res.items);
    } catch (err) {
      setError('Error al cargar recomendaciones.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (isLoading) return <NarrativeSkeleton />;
  if (error) return <div className="text-danger text-center py-12">{error}</div>;

  // Calculate confidence and classify by impact
  const classifyImpact = (rec: ObservatoryRecommendation): ImpactLevel => {
    const confidence = rec.recommendation_confidence 
      ? parseFloat(rec.recommendation_confidence) 
      : (rec.confidence || 0);
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  };

  // Filter recommendations
  const filteredRecs = filterType === 'all' 
    ? recommendations 
    : recommendations.filter(r => r.recommendation_type === filterType);

  // Sort by confidence (impact)
  const sortedRecs = [...filteredRecs].sort((a, b) => {
    const confA = a.recommendation_confidence ? parseFloat(a.recommendation_confidence) : (a.confidence || 0);
    const confB = b.recommendation_confidence ? parseFloat(b.recommendation_confidence) : (b.confidence || 0);
    return confB - confA;
  });

  // Group by type
  const recsByType = recommendations.reduce((acc, r) => {
    const type = r.recommendation_type || 'other';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Group by impact
  const recsByImpact = {
    high: recommendations.filter(r => classifyImpact(r) === 'high').length,
    medium: recommendations.filter(r => classifyImpact(r) === 'medium').length,
    low: recommendations.filter(r => classifyImpact(r) === 'low').length,
  };

  // Average confidence
  const avgConfidence = recommendations.length > 0
    ? Math.round(recommendations.reduce((sum, r) => {
        const conf = r.recommendation_confidence ? parseFloat(r.recommendation_confidence) : (r.confidence || 0);
        return sum + conf;
      }, 0) / recommendations.length * 100)
    : 0;

  // Generate narrative
  const generateInsight = () => {
    const highImpact = recsByImpact.high;
    if (highImpact > 0) {
      return `Se identificaron ${highImpact} recomendacion${highImpact !== 1 ? 'es' : ''} de alto impacto con confianza superior al 80%. Implementar estas acciones puede mejorar significativamente la alineacion curricular.`;
    }
    return `El sistema genero ${recommendations.length} sugerencias con confianza promedio del ${avgConfidence}%. Se recomienda priorizar acciones de tipo curriculum.`;
  };

  // Chart data
  const typeChartData = Object.entries(recsByType).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  }));

  const impactChartData = [
    { name: 'Alto', value: recsByImpact.high, color: '#10B981' },
    { name: 'Medio', value: recsByImpact.medium, color: '#3B82F6' },
    { name: 'Bajo', value: recsByImpact.low, color: '#F59E0B' },
  ].filter(d => d.value > 0);

  const COLORS = ['#003A70', '#10B981', '#F59E0B', '#DC2626', '#8B5CF6'];

  return (
    <div className="space-y-8">
      {/* Main Insight */}
      <InsightCard
        headline={generateInsight()}
        variant={recsByImpact.high > 3 ? 'success' : 'default'}
        metric={{
          value: recommendations.length,
          label: 'Recomendaciones Totales',
        }}
      />

      {/* Recommendation KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StoryMetric
          icon={<Lightbulb className="w-5 h-5 text-primary" />}
          value={recommendations.length}
          label="Total"
          context="Sugerencias generadas"
        />
        <StoryMetric
          icon={<Target className="w-5 h-5 text-success" />}
          value={recsByImpact.high}
          label="Alto Impacto"
          context="Confianza >= 80%"
        />
        <StoryMetric
          icon={<CheckCircle className="w-5 h-5 text-primary" />}
          value={`${avgConfidence}%`}
          label="Confianza"
          context="Promedio del sistema"
        />
        <StoryMetric
          icon={<Clock className="w-5 h-5 text-warning" />}
          value={Object.keys(recsByType).length}
          label="Tipos"
          context="Categorias de accion"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* By Type */}
        <NarrativeSection
          title="Distribucion por Tipo"
          subtitle="Clasificacion de recomendaciones por categoria"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {typeChartData.length > 0 ? (
              <div className="flex items-center gap-8">
                <ResponsiveContainer width="50%" height={200}>
                  <PieChart>
                    <Pie
                      data={typeChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      dataKey="value"
                      labelLine={false}
                    >
                      {typeChartData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2">
                  {typeChartData.map((item, idx) => (
                    <div key={item.name} className="flex items-center gap-3">
                      <span 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: COLORS[idx % COLORS.length] }} 
                      />
                      <span className="text-sm text-foreground">{item.name}</span>
                      <span className="text-sm font-bold text-foreground">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-center text-muted py-12">Sin recomendaciones</p>
            )}
          </div>
        </NarrativeSection>

        {/* By Impact */}
        <NarrativeSection
          title="Distribucion por Impacto"
          subtitle="Clasificacion segun nivel de confianza"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {impactChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={impactChartData} layout="vertical" margin={{ left: 60 }}>
                  <XAxis type="number" fontSize={12} />
                  <YAxis type="category" dataKey="name" fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="value" name="Recomendaciones" radius={[0, 4, 4, 0]}>
                    {impactChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-muted py-12">Sin datos de impacto</p>
            )}
          </div>
        </NarrativeSection>
      </div>

      {/* Recommendations List */}
      <NarrativeSection
        title="Centro de Recomendaciones"
        subtitle="Acciones priorizadas por impacto y confianza"
      >
        {/* Filter Tabs */}
        <div className="flex items-center gap-2 mb-4">
          <Filter size={16} className="text-muted" />
          {(['all', 'student', 'career', 'curriculum'] as FilterType[]).map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                filterType === type
                  ? 'bg-primary text-white'
                  : 'bg-subtle text-muted hover:text-foreground'
              }`}
            >
              {type === 'all' ? 'Todas' : type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>

        {/* Recommendations Cards */}
        <div className="space-y-4">
          {sortedRecs.length > 0 ? (
            sortedRecs.map((rec, idx) => {
              const confidence = rec.recommendation_confidence 
                ? Math.round(parseFloat(rec.recommendation_confidence) * 100) 
                : Math.round((rec.confidence || 0) * 100);
              const impact = classifyImpact(rec);
              const title = rec.target_role || rec.recommendation_type || 'Recomendacion';
              const reasoning = rec.recommendation_reasoning || 
                rec.recommendation_payload?.why_recommended?.join(' ') || '';

              return (
                <div 
                  key={idx} 
                  className={`bg-white rounded-lg border border-line p-5 border-l-4 ${
                    impact === 'high' ? 'border-l-success' : 
                    impact === 'medium' ? 'border-l-primary' : 'border-l-warning'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-xs font-semibold text-primary uppercase">
                          {rec.recommendation_type}
                        </span>
                        <RiskBadge 
                          level={impact === 'high' ? 'low' : impact === 'medium' ? 'medium' : 'high'}
                          label={impact === 'high' ? 'Alto impacto' : impact === 'medium' ? 'Medio' : 'Bajo'}
                        />
                      </div>
                      <h4 className="text-base font-semibold text-foreground mb-2">{title}</h4>
                      {reasoning && (
                        <p className="text-sm text-muted line-clamp-2">{reasoning}</p>
                      )}
                      {rec.recommendation_payload?.recommended_skills && rec.recommendation_payload.recommended_skills.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {rec.recommendation_payload.recommended_skills.slice(0, 4).map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 text-xs bg-subtle rounded text-muted">
                              {skill}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className={`text-2xl font-bold ${
                        confidence >= 80 ? 'text-success' : 
                        confidence >= 50 ? 'text-primary' : 'text-warning'
                      }`}>
                        {confidence}%
                      </p>
                      <p className="text-xs text-muted">confianza</p>
                    </div>
                  </div>
                  {rec.target_company && (
                    <div className="flex items-center gap-2 mt-4 pt-4 border-t border-line">
                      <ArrowUpRight size={14} className="text-muted" />
                      <span className="text-xs text-muted">Empresa relacionada:</span>
                      <span className="text-xs font-medium text-foreground">{rec.target_company}</span>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <div className="bg-white rounded-lg border border-line p-8 text-center">
              <AlertCircle size={32} className="text-muted mx-auto mb-3" />
              <p className="text-muted">No hay recomendaciones para el filtro seleccionado</p>
            </div>
          )}
        </div>
      </NarrativeSection>
    </div>
  );
}
