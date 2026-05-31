import { useMemo, useState } from 'react';
import { Bot, SendHorizontal, Sparkles } from 'lucide-react';

import type { AskObservatoryResponse } from '../../types/api';

interface AcademicCopilotPanelProps {
  title: string;
  subtitle: string;
  loading?: boolean;
  error?: string | null;
  answer?: AskObservatoryResponse | null;
  onAsk: (question: string) => Promise<AskObservatoryResponse | null>;
  suggestedQuestions?: string[];
}

export function AcademicCopilotPanel({
  title,
  subtitle,
  loading = false,
  error = null,
  answer = null,
  onAsk,
  suggestedQuestions = [],
}: AcademicCopilotPanelProps) {
  const [question, setQuestion] = useState(suggestedQuestions[0] || '');
  const [submitting, setSubmitting] = useState(false);
  const quickQuestions = useMemo(
    () =>
      suggestedQuestions.slice(0, 4),
    [suggestedQuestions],
  );

  async function submitQuestion(value?: string) {
    const query = (value ?? question).trim();
    if (!query || submitting) return;
    setQuestion(query);
    setSubmitting(true);
    try {
      await onAsk(query);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            <Bot size={14} strokeWidth={2} />
            Copiloto académico
          </div>
          <h3 className="mt-2 text-lg font-semibold text-ink">{title}</h3>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{subtitle}</p>
        </div>
        <span className="rounded-full bg-brand/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
          OpenAI
        </span>
      </div>

      <form
        className="flex flex-col gap-3 lg:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          void submitQuestion();
        }}
      >
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          className="min-h-[96px] flex-1 rounded-lg border border-line bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-brand"
          placeholder="Escribe una pregunta institucional sobre programas, brechas o impacto esperado."
        />
        <button
          type="submit"
          disabled={loading || submitting}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-60 lg:self-start"
        >
          <SendHorizontal size={16} strokeWidth={2} />
          {submitting || loading ? 'Consultando...' : 'Preguntar'}
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        {quickQuestions.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => void submitQuestion(item)}
            className="rounded-full border border-line bg-slate-50 px-3 py-1 text-xs font-medium text-muted transition hover:border-brand/40 hover:bg-brand/5"
          >
            <Sparkles size={12} className="mr-1 inline-block" />
            {item}
          </button>
        ))}
      </div>

      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-7 text-amber-900">
          Análisis generado con narrativa determinística. Configure OpenAI para explicación avanzada.
        </div>
      ) : null}

      {answer ? (
        <div className="space-y-3 rounded-lg border border-line bg-slate-50 p-4">
          <p className="text-sm leading-7 text-ink">{answer.answer}</p>
          <div className="flex flex-wrap gap-2">
            {answer.evidence_sources.slice(0, 6).map((source) => (
              <span key={source} className="rounded-full bg-white px-3 py-1 text-xs font-medium text-muted">
                {source}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted">
          Haz una pregunta para ver una respuesta explicada con evidencia real.
        </p>
      )}
    </section>
  );
}
