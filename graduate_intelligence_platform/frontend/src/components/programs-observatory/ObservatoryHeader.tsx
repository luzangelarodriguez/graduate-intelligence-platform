import { Target, TrendingUp, AlertCircle, BarChart3 } from 'lucide-react';

interface ObservatoryHeaderProps {
  totalPrograms: number;
  averageAlignment: number;
  criticalCount: number;
  opportunityCount: number;
}

export function ObservatoryHeader({
  totalPrograms,
  averageAlignment,
  criticalCount,
  opportunityCount,
}: ObservatoryHeaderProps) {
  return (
    <div className="space-y-6 border-b border-slate-200 pb-6">
      {/* Title and Description */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-slate-900">Program Observatory</h1>
        <p className="text-base text-slate-600">
          Executive intelligence dashboard for program alignment, market signals, and strategic positioning
        </p>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg bg-gradient-to-br from-blue-50 to-blue-25 border border-blue-100 p-4">
          <span className="block text-xs font-semibold uppercase tracking-wide text-slate-600">Total Programs</span>
          <strong className="mt-2 block text-2xl font-bold text-blue-900">{totalPrograms}</strong>
          <span className="mt-1 block text-xs text-slate-600">Under active monitoring</span>
        </div>

        <div className="rounded-lg bg-gradient-to-br from-emerald-50 to-emerald-25 border border-emerald-100 p-4">
          <span className="block text-xs font-semibold uppercase tracking-wide text-slate-600">Avg. Alignment</span>
          <strong className="mt-2 block text-2xl font-bold text-emerald-900">{averageAlignment.toFixed(1)}%</strong>
          <span className="mt-1 block text-xs text-slate-600">Market positioning</span>
        </div>

        <div className="rounded-lg bg-gradient-to-br from-amber-50 to-amber-25 border border-amber-100 p-4">
          <span className="block text-xs font-semibold uppercase tracking-wide text-slate-600">Opportunities</span>
          <strong className="mt-2 block text-2xl font-bold text-amber-900">{opportunityCount}</strong>
          <span className="mt-1 block text-xs text-slate-600">High alignment programs</span>
        </div>

        <div className="rounded-lg bg-gradient-to-br from-rose-50 to-rose-25 border border-rose-100 p-4">
          <span className="block text-xs font-semibold uppercase tracking-wide text-slate-600">Critical</span>
          <strong className="mt-2 block text-2xl font-bold text-rose-900">{criticalCount}</strong>
          <span className="mt-1 block text-xs text-slate-600">Requires attention</span>
        </div>
      </div>
    </div>
  );
}
