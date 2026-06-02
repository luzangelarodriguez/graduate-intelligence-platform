import { TrendingUp, Zap, AlertTriangle } from 'lucide-react';
import type { Program } from '../../types/api';

interface MarketIntelligencePanelProps {
  selectedProgram: Program | null;
  topGap: string;
  topRecommendation: string;
}

export function MarketIntelligencePanel({
  selectedProgram,
  topGap,
  topRecommendation,
}: MarketIntelligencePanelProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm p-6 space-y-4">
      <div>
        <h3 className="text-lg font-bold text-slate-900">Market Intelligence</h3>
        <p className="text-sm text-slate-600 mt-1">Labor market trends and strategic insights</p>
      </div>

      {selectedProgram ? (
        <div className="space-y-4">
          {/* Key Signals */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-3 flex items-start gap-3">
              <TrendingUp className="text-emerald-600 mt-0.5 shrink-0" size={18} />
              <div>
                <p className="text-xs font-semibold uppercase text-slate-600">Labor Demand</p>
                <p className="text-sm text-slate-700 mt-1">
                  {selectedProgram.total_empleos_relacionados ? 'Strong market demand' : 'Monitoring status'}
                </p>
              </div>
            </div>
            <div className="rounded-lg bg-blue-50 border border-blue-100 p-3 flex items-start gap-3">
              <Zap className="text-blue-600 mt-0.5 shrink-0" size={18} />
              <div>
                <p className="text-xs font-semibold uppercase text-slate-600">Forecast Signal</p>
                <p className="text-sm text-slate-700 mt-1">
                  {selectedProgram.total_empleos_relacionados ? 'Positive' : 'Neutral'}
                </p>
              </div>
            </div>
          </div>

          {/* Primary Gap Analysis */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
            <div className="flex items-start gap-2 mb-2">
              <AlertTriangle size={16} className="text-slate-600 mt-0.5 shrink-0" />
              <p className="text-xs font-semibold uppercase text-slate-600">Curriculum Gap</p>
            </div>
            <p className="text-sm text-slate-700 leading-relaxed">{topGap}</p>
          </div>

          {/* Strategic Recommendation */}
          <div className="rounded-lg bg-amber-50 border border-amber-100 p-4">
            <p className="text-xs font-semibold uppercase text-amber-900 mb-2">Priority Action</p>
            <p className="text-sm text-amber-900 leading-relaxed">{topRecommendation}</p>
          </div>

          {/* Market Context */}
          <div className="space-y-2 text-sm">
            <p className="font-medium text-slate-900">Market Context</p>
            <ul className="space-y-1 text-slate-700 text-sm">
              <li className="flex gap-2">
                <span className="text-slate-400">•</span>
                <span>Continuous monitoring of {selectedProgram.rol || 'sector'} market developments</span>
              </li>
              <li className="flex gap-2">
                <span className="text-slate-400">•</span>
                <span>Cross-referencing with industry standards and emerging skills</span>
              </li>
              <li className="flex gap-2">
                <span className="text-slate-400">•</span>
                <span>Alignment with institutional strategic positioning</span>
              </li>
            </ul>
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-sm text-slate-600">Select a program to view market intelligence</p>
        </div>
      )}
    </div>
  );
}
