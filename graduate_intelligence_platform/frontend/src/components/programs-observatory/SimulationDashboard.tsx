interface SimulationMetrics {
  currentAlignment: number;
  projectedAlignment: number;
  currentRisk: number;
  projectedRisk: number;
  currentEmployability: number;
  projectedEmployability: number;
  currentGaps: number;
  projectedGaps: number;
}

interface SimulationDashboardProps {
  metrics: SimulationMetrics;
}

export function SimulationDashboard({ metrics }: SimulationDashboardProps) {
  const calculateChange = (current: number, projected: number) => {
    const change = projected - current;
    return { change, percent: ((change / current) * 100).toFixed(1) };
  };

  const alignmentChange = calculateChange(metrics.currentAlignment, metrics.projectedAlignment);
  const riskChange = calculateChange(metrics.currentRisk, metrics.projectedRisk);
  const employabilityChange = calculateChange(metrics.currentEmployability, metrics.projectedEmployability);
  const gapsChange = calculateChange(metrics.currentGaps, metrics.projectedGaps);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 mb-6">Simulation Dashboard: Current vs Projected</h3>

      <div className="grid grid-cols-2 gap-6">
        {/* Alignment */}
        <div className="space-y-3">
          <p className="text-sm font-semibold text-slate-700">Alignment Score</p>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Current</span>
              <span className="font-semibold text-slate-900">{metrics.currentAlignment.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-blue-500 rounded-full" style={{ width: `${metrics.currentAlignment}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{metrics.projectedAlignment.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-green-500 rounded-full" style={{ width: `${metrics.projectedAlignment}%` }} />
            </div>
          </div>
          <div className={`text-xs font-semibold p-2 rounded ${
            alignmentChange.change > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {alignmentChange.change > 0 ? '+' : ''}{alignmentChange.change.toFixed(1)} ({alignmentChange.percent}%)
          </div>
        </div>

        {/* Risk */}
        <div className="space-y-3">
          <p className="text-sm font-semibold text-slate-700">Risk Score</p>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Current</span>
              <span className="font-semibold text-slate-900">{metrics.currentRisk.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-red-500 rounded-full" style={{ width: `${metrics.currentRisk}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{metrics.projectedRisk.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-amber-500 rounded-full" style={{ width: `${metrics.projectedRisk}%` }} />
            </div>
          </div>
          <div className={`text-xs font-semibold p-2 rounded ${
            riskChange.change < 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {riskChange.change < 0 ? '' : '+'}{riskChange.change.toFixed(1)} ({riskChange.percent}%)
          </div>
        </div>

        {/* Employability */}
        <div className="space-y-3">
          <p className="text-sm font-semibold text-slate-700">Employability</p>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Current</span>
              <span className="font-semibold text-slate-900">{metrics.currentEmployability.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-green-500 rounded-full" style={{ width: `${metrics.currentEmployability}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{metrics.projectedEmployability.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-emerald-500 rounded-full" style={{ width: `${metrics.projectedEmployability}%` }} />
            </div>
          </div>
          <div className={`text-xs font-semibold p-2 rounded ${
            employabilityChange.change > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {employabilityChange.change > 0 ? '+' : ''}{employabilityChange.change.toFixed(1)} ({employabilityChange.percent}%)
          </div>
        </div>

        {/* Gaps */}
        <div className="space-y-3">
          <p className="text-sm font-semibold text-slate-700">Curriculum Gaps</p>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Current</span>
              <span className="font-semibold text-slate-900">{metrics.currentGaps}</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-red-500 rounded-full" style={{ width: `${Math.min(100, (metrics.currentGaps / 30) * 100)}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{metrics.projectedGaps}</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-amber-500 rounded-full" style={{ width: `${Math.min(100, (metrics.projectedGaps / 30) * 100)}%` }} />
            </div>
          </div>
          <div className={`text-xs font-semibold p-2 rounded ${
            gapsChange.change < 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {gapsChange.change < 0 ? '' : '+'}{gapsChange.change.toFixed(0)} ({gapsChange.percent}%)
          </div>
        </div>
      </div>
    </div>
  );
}
