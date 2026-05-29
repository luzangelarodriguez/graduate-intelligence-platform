import { useMemo } from 'react';
import {
  ArrowRight,
  Building2,
  GraduationCap,
  Lightbulb,
  RefreshCw,
  Sparkles,
  Target,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import {
  EmptyState,
  KpiCard,
  KpiGrid,
  SectionHeader,
  SkeletonCard,
  SkeletonKpiGrid,
  StatusBadge,
} from '../components/ui';
import { useRecomendaciones } from '../hooks/useRecomendaciones';

export function RecomendacionesPage() {
  const {
    recommendations,
    selectedType,
    setSelectedType,
    isLoading,
    error,
    refresh,
  } = useRecomendaciones();

  // Get unique recommendation types
  const types = useMemo(() => {
    const typeSet = new Set(recommendations.map((r) => r.recommendation_type).filter(Boolean));
    return Array.from(typeSet);
  }, [recommendations]);

  // Filter recommendations
  const filteredRecommendations = useMemo(() => {
    if (!selectedType) return recommendations;
    return recommendations.filter((r) => r.recommendation_type === selectedType);
  }, [recommendations, selectedType]);

  // Group by impact level
  const groupedByImpact = useMemo(() => {
    const high = filteredRecommendations.filter(
      (r) => r.impact_level === 'alto' || r.impact_level === 'high'
    );
    const medium = filteredRecommendations.filter(
      (r) => r.impact_level === 'medio' || r.impact_level === 'medium'
    );
    const low = filteredRecommendations.filter(
      (r) =>
        r.impact_level === 'bajo' ||
        r.impact_level === 'low' ||
        !r.impact_level
    );
    return { high, medium, low };
  }, [filteredRecommendations]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <div className="skeleton skeleton-title w-64 mb-2" />
          <div className="skeleton skeleton-text w-96" />
        </div>
        <SkeletonKpiGrid count={4} />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} lines={4} />
          ))}
        </div>
      </div>
    );
  }

  if (error && !recommendations.length) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h1 className="page-title">Recomendaciones IA</h1>
          <p className="page-subtitle">Sugerencias generadas por inteligencia artificial</p>
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

  const totalRecommendations = recommendations.length;
  const highImpactCount = groupedByImpact.high.length;
  const avgConfidence =
    recommendations.reduce((sum, r) => {
      const conf = r.recommendation_confidence ? parseFloat(r.recommendation_confidence) : (r.confidence || 0);
      return sum + conf;
    }, 0) / (totalRecommendations || 1);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="page-title">Recomendaciones IA</h1>
            <p className="page-subtitle text-balance">
              Sugerencias automatizadas para mejorar la pertinencia curricular y alineacion con el mercado laboral.
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
          label="Total Recomendaciones"
          value={totalRecommendations}
          description="Sugerencias generadas"
          icon={<Lightbulb size={18} />}
          featured
        />
        <KpiCard
          label="Alto Impacto"
          value={highImpactCount}
          description="Prioridad critica"
          icon={<Target size={18} />}
        />
        <KpiCard
          label="Confianza Promedio"
          value={`${(avgConfidence * 100).toFixed(0)}%`}
          description="Nivel de certeza IA"
          icon={<Sparkles size={18} />}
        />
        <KpiCard
          label="Tipos de Accion"
          value={types.length}
          description="Categorias distintas"
          icon={<GraduationCap size={18} />}
        />
      </KpiGrid>

      {/* Filter by Type */}
      <div className="filter-bar">
        <div className="filter-item">
          <label>Filtrar por tipo</label>
          <select
            className="form-select max-w-xs"
            value={selectedType || ''}
            onChange={(e) => setSelectedType(e.target.value || null)}
          >
            <option value="">Todos los tipos</option>
            {types.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* High Impact Recommendations */}
      {groupedByImpact.high.length > 0 && (
        <section>
          <SectionHeader
            title="Alto Impacto"
            description="Recomendaciones prioritarias para atencion inmediata"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {groupedByImpact.high.map((rec, i) => (
              <RecommendationCard key={`high-${i}`} recommendation={rec} impact="high" />
            ))}
          </div>
        </section>
      )}

      {/* Medium Impact Recommendations */}
      {groupedByImpact.medium.length > 0 && (
        <section>
          <SectionHeader
            title="Impacto Medio"
            description="Sugerencias para planificacion a mediano plazo"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {groupedByImpact.medium.map((rec, i) => (
              <RecommendationCard key={`medium-${i}`} recommendation={rec} impact="medium" />
            ))}
          </div>
        </section>
      )}

      {/* Low Impact Recommendations */}
      {groupedByImpact.low.length > 0 && (
        <section>
          <SectionHeader
            title="Otras Recomendaciones"
            description="Sugerencias complementarias"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {groupedByImpact.low.map((rec, i) => (
              <RecommendationCard key={`low-${i}`} recommendation={rec} impact="low" />
            ))}
          </div>
        </section>
      )}

      {/* Empty State */}
      {filteredRecommendations.length === 0 && (
        <div className="exec-card p-6">
          <EmptyState
            title="Sin recomendaciones"
            body="El observatorio aun no ha generado recomendaciones con los filtros seleccionados."
          />
        </div>
      )}

      {/* Quick Links */}
      <section className="exec-card p-5">
        <SectionHeader
          title="Herramientas Relacionadas"
          description="Accede a funciones avanzadas del observatorio"
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link
            to="/brechas-curriculares"
            className="flex items-center justify-between p-4 rounded border border-line hover:border-accent hover:bg-accent-light transition"
          >
            <div className="flex items-center gap-3">
              <Target size={20} className="text-accent" />
              <span className="font-semibold text-ink">Brechas Curriculares</span>
            </div>
            <ArrowRight size={16} className="text-muted" />
          </Link>
          <Link
            to="/mercado-laboral"
            className="flex items-center justify-between p-4 rounded border border-line hover:border-accent hover:bg-accent-light transition"
          >
            <div className="flex items-center gap-3">
              <Building2 size={20} className="text-accent" />
              <span className="font-semibold text-ink">Mercado Laboral</span>
            </div>
            <ArrowRight size={16} className="text-muted" />
          </Link>
          <Link
            to="/oferta-academica"
            className="flex items-center justify-between p-4 rounded border border-line hover:border-accent hover:bg-accent-light transition"
          >
            <div className="flex items-center gap-3">
              <GraduationCap size={20} className="text-accent" />
              <span className="font-semibold text-ink">Oferta Academica</span>
            </div>
            <ArrowRight size={16} className="text-muted" />
          </Link>
        </div>
      </section>
    </div>
  );
}

interface RecommendationCardProps {
  recommendation: {
    recommendation_type?: string;
    target_role?: string;
    target_company?: string;
    recommendation_reasoning?: string;
    recommendation_confidence?: string;
    recommendation_payload?: {
      why_recommended?: string[];
      recommended_skills?: string[];
      market_alignment_score?: number;
    };
  };
  impact: 'high' | 'medium' | 'low';
}

function RecommendationCard({ recommendation, impact }: RecommendationCardProps) {
  const borderClass =
    impact === 'high'
      ? 'border-l-4 border-l-danger'
      : impact === 'medium'
      ? 'border-l-4 border-l-warning'
      : 'border-l-4 border-l-line';

  const confidence = recommendation.recommendation_confidence 
    ? parseFloat(recommendation.recommendation_confidence)
    : null;

  const title = recommendation.target_role || recommendation.recommendation_type || 'Recomendacion';
  const description = recommendation.recommendation_reasoning || 
    recommendation.recommendation_payload?.why_recommended?.join(' ') || '';

  return (
    <article className={`rec-card ${borderClass}`}>
      <div className="rec-card-header">
        <div className="flex-1">
          {recommendation.recommendation_type && (
            <span className="rec-card-type">{recommendation.recommendation_type.toUpperCase()}</span>
          )}
          <h4 className="rec-card-title">{title}</h4>
        </div>
        {confidence !== null && (
          <StatusBadge
            status={confidence >= 0.7 ? 'success' : 'neutral'}
            label={`${(confidence * 100).toFixed(0)}%`}
          />
        )}
      </div>
      {description && <p className="rec-card-body">{description}</p>}
      {(recommendation.target_company || recommendation.recommendation_payload?.recommended_skills?.length) && (
        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-line">
          {recommendation.target_company && (
            <span className="badge badge-accent">
              <Building2 size={10} />
              {recommendation.target_company}
            </span>
          )}
          {recommendation.recommendation_payload?.recommended_skills?.slice(0, 3).map((skill) => (
            <span key={skill} className="badge badge-neutral">
              {skill}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
