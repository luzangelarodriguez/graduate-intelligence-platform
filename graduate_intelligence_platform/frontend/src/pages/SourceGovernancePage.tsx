import { useEffect, useMemo, useState } from 'react';
import { Activity, DatabaseZap, LockKeyhole, ShieldCheck, Signal, TriangleAlert } from 'lucide-react';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { getSourceGovernanceDashboard } from '../services/api';
import type { SourceGovernanceRow } from '../types/api';

function percent(value: number) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function score(value: number) {
  return Number(value || 0).toFixed(2);
}

function tierLabel(tier: SourceGovernanceRow['source_tier']) {
  if (tier === 'Gold') return 'Gold';
  if (tier === 'Silver') return 'Silver';
  if (tier === 'Bronze') return 'Bronze';
  return 'Experimental';
}

export function SourceGovernancePage() {
  const [sources, setSources] = useState<SourceGovernanceRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    getSourceGovernanceDashboard()
      .then((data) => {
        if (!mounted) return;
        setSources(data);
        setError('');
      })
      .catch((cause) => {
        if (!mounted) return;
        setError(cause instanceof Error ? cause.message : 'No fue posible cargar la gobernanza de fuentes.');
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const rankedSources = useMemo(
    () => [...sources].sort((left, right) => right.reliability_score - left.reliability_score),
    [sources],
  );

  const summary = useMemo(() => {
    const total = sources.length;
    const blocked = sources.filter((item) => item.blocked_auth_rate > 0.05).length;
    const ready = sources.filter((item) => item.gold_readiness).length;
    const bronzeOrBetter = sources.filter((item) => ['Gold', 'Silver', 'Bronze'].includes(item.source_tier)).length;
    const avgReliability = sources.reduce((sum, item) => sum + Number(item.reliability_score || 0), 0) / Math.max(1, total);
    return { total, blocked, ready, bronzeOrBetter, avgReliability };
  }, [sources]);

  if (isLoading) return <LoadingState label="Cargando gobernanza de fuentes..." />;
  if (error) return <EmptyState title="No se pudo cargar gobernanza de fuentes" body={error} />;

  return (
    <section className="source-governance-page">
      <div className="governance-hero">
        <div>
          <span>Motor de confiabilidad de evidencia laboral</span>
          <h2>Gobernanza de fuentes</h2>
          <p>
            Evaluacion tecnica de confiabilidad, frescura, contaminacion y readiness antes de alimentar KPIs
            institucionales de pertinencia academica.
          </p>
        </div>
        <div className="governance-hero-score">
          <span>Reliability promedio</span>
          <strong>{score(summary.avgReliability)}</strong>
          <small>{summary.ready} fuentes listas para Gold</small>
        </div>
      </div>

      <div className="governance-kpi-grid">
        <article>
          <ShieldCheck size={18} strokeWidth={1.8} />
          <span>Fuentes evaluadas</span>
          <strong>{summary.total}</strong>
        </article>
        <article>
          <DatabaseZap size={18} strokeWidth={1.8} />
          <span>Bronze o superior</span>
          <strong>{summary.bronzeOrBetter}</strong>
        </article>
        <article>
          <LockKeyhole size={18} strokeWidth={1.8} />
          <span>Bloqueadas por auth</span>
          <strong>{summary.blocked}</strong>
        </article>
        <article>
          <Signal size={18} strokeWidth={1.8} />
          <span>Gold readiness</span>
          <strong>{summary.ready}</strong>
        </article>
      </div>

      <div className="governance-layout">
        <div className="governance-source-list">
          {rankedSources.map((source) => (
            <article className={`governance-source-card ${source.source_tier.toLowerCase()}`} key={source.source}>
              <div className="governance-source-head">
                <div>
                  <span>{tierLabel(source.source_tier)}</span>
                  <strong>{source.source}</strong>
                </div>
                <b>{score(source.reliability_score)}</b>
              </div>
              <p>{source.notes}</p>
              <div className="governance-bars">
                <label>
                  <span>Freshness</span>
                  <i>
                    <em style={{ width: percent(source.freshness_score) }} />
                  </i>
                  <b>{percent(source.freshness_score)}</b>
                </label>
                <label>
                  <span>Evidencia</span>
                  <i>
                    <em style={{ width: percent(source.evidence_quality) }} />
                  </i>
                  <b>{percent(source.evidence_quality)}</b>
                </label>
                <label>
                  <span>Completitud</span>
                  <i>
                    <em style={{ width: percent(source.extraction_completeness) }} />
                  </i>
                  <b>{percent(source.extraction_completeness)}</b>
                </label>
              </div>
            </article>
          ))}
        </div>

        <aside className="governance-risk-panel">
          <div className="section-head">
            <div>
              <h3>Alertas de gobierno</h3>
              <p>Riesgos que bloquean la promocion a KPIs productivos.</p>
            </div>
          </div>
          <div className="governance-alerts">
            {rankedSources
              .filter((source) => !source.gold_readiness)
              .map((source) => (
                <article key={source.source}>
                  {source.blocked_auth_rate > 0.05 ? (
                    <LockKeyhole size={17} strokeWidth={1.8} />
                  ) : source.contamination_rate > 0.12 ? (
                    <TriangleAlert size={17} strokeWidth={1.8} />
                  ) : (
                    <Activity size={17} strokeWidth={1.8} />
                  )}
                  <div>
                    <strong>{source.source}</strong>
                    <span>
                      {source.blocked_auth_rate > 0.05
                        ? `Blocked auth ${percent(source.blocked_auth_rate)}`
                        : source.contamination_rate > 0.12
                          ? `Contaminacion ${percent(source.contamination_rate)}`
                          : `Freshness ${percent(source.freshness_score)}`}
                    </span>
                  </div>
                </article>
              ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
