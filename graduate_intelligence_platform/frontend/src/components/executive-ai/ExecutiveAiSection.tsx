import { EmptyState } from '../EmptyState';
import { LoadingState } from '../LoadingState';
import { SectionTitle } from '../program-intelligence/ProgramIntelligenceBlocks';

interface ExecutiveAiSectionProps {
  title: string;
  subtitle: string;
  body?: string;
  evidenceSources?: string[];
  confidence?: number | null;
  model?: string | null;
  loading?: boolean;
  error?: string | null;
  emptyTitle: string;
  emptyBody: string;
  badgeLabel?: string;
}

function toPercent(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return 'N/D';
  }
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

export function ExecutiveAiSection({
  title,
  subtitle,
  body,
  evidenceSources = [],
  confidence,
  model,
  loading = false,
  error = null,
  emptyTitle,
  emptyBody,
  badgeLabel = 'IA ejecutiva',
}: ExecutiveAiSectionProps) {
  if (loading) {
    return (
      <section className="panel space-y-4">
        <LoadingState label="Generando explicación ejecutiva..." />
      </section>
    );
  }

  const fallbackMode = Boolean(error) || model === 'deterministic-fallback';

  return (
    <section className="panel space-y-4">
      <SectionTitle
        title={title}
        subtitle={subtitle}
      />
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-brand/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">{badgeLabel}</span>
        <span className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-medium text-muted">
          Confianza {toPercent(confidence)}
        </span>
        {model === 'deterministic-fallback' ? (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
            Análisis generado con narrativa determinística. Configure OpenAI para explicación avanzada.
          </span>
        ) : null}
        {error ? (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
            Respuesta explicada con datos disponibles mientras se recupera OpenAI.
          </span>
        ) : null}
      </div>
      {body ? (
        <p className="text-sm leading-7 text-ink">{body}</p>
      ) : (
        <EmptyState
          title={emptyTitle}
          body={
            fallbackMode
              ? 'Análisis generado con narrativa determinística. Configure OpenAI para explicación avanzada.'
              : emptyBody
          }
        />
      )}
      <div className="flex flex-wrap gap-2">
        {evidenceSources.length ? (
          evidenceSources.slice(0, 6).map((source) => (
            <span key={source} className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-medium text-muted">
              {source}
            </span>
          ))
        ) : (
          <span className="text-xs text-muted">Sin fuentes explícitas.</span>
        )}
      </div>
    </section>
  );
}
