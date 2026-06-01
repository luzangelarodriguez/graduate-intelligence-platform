import { Loader2 } from 'lucide-react';
import { useProgramSimulation } from '../../hooks/useProgramSimulation';

interface SimulationDashboardProps {
  programId: number | null;
  proposedSkills?: string[];
  horizonMonths?: number;
}

export function SimulationDashboard({ programId, proposedSkills = [], horizonMonths = 12 }: SimulationDashboardProps) {
  const { simulation, isLoading, error } = useProgramSimulation(programId, proposedSkills, horizonMonths);

  if (!programId) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 text-center">
        <p className="text-slate-600">Select a program to view simulation</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 flex items-center justify-center gap-3">
        <Loader2 size={20} className="animate-spin text-blue-600" />
        <p className="text-slate-600">Loading simulation...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="text-red-900 font-semibold">Error loading simulation</p>
        <p className="text-sm text-red-700 mt-2">{error.message}</p>
      </div>
    );
  }

  if (!simulation) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 text-center">
        <p className="text-slate-600">No simulation data available</p>
      </div>
    );
  }

  const calculateChange = (current: number | null | undefined, projected: number | null | undefined) => {
    if (current === null || current === undefined || projected === null || projected === undefined || current === 0) {
      return { change: 0, percent: 'N/D' };
    }
    const change = projected - current;
    const percent = ((change / current) * 100).toFixed(1);
    return { change, percent };
  };

  const currentAlignment = simulation.current_alignment ?? 0;
  const projectedAlignment = simulation.projected_alignment ?? 0;
  const currentRisk = simulation.current_risk ?? 0;
  const projectedRisk = simulation.projected_risk ?? 0;
  const currentEmployability = simulation.current_employability ?? 0;
  const projectedEmployability = simulation.projected_employability ?? 0;
  const currentGaps = simulation.current_gaps ?? 0;
  const projectedGaps = simulation.projected_gaps ?? 0;

  const alignmentChange = calculateChange(currentAlignment, projectedAlignment);
  const riskChange = calculateChange(currentRisk, projectedRisk);
  const employabilityChange = calculateChange(currentEmployability, projectedEmployability);
  const gapsChange = calculateChange(currentGaps, projectedGaps);

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
              <span className="font-semibold text-slate-900">{currentAlignment !== null ? currentAlignment.toFixed(1) : 'N/D'}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-blue-500 rounded-full" style={{ width: `${Math.min(100, currentAlignment || 0)}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{projectedAlignment !== null ? projectedAlignment.toFixed(1) : 'N/D'}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-green-500 rounded-full" style={{ width: `${Math.min(100, projectedAlignment || 0)}%` }} />
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
              <span className="font-semibold text-slate-900">{currentRisk !== null ? currentRisk.toFixed(1) : 'N/D'}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-red-500 rounded-full" style={{ width: `${Math.min(100, currentRisk || 0)}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{projectedRisk !== null ? projectedRisk.toFixed(1) : 'N/D'}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-amber-500 rounded-full" style={{ width: `${Math.min(100, projectedRisk || 0)}%` }} />
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
              <span className="font-semibold text-slate-900">{currentEmployability !== null ? currentEmployability.toFixed(1) : 'N/D'}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-green-500 rounded-full" style={{ width: `${Math.min(100, currentEmployability || 0)}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{projectedEmployability !== null ? projectedEmployability.toFixed(1) : 'N/D'}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-emerald-500 rounded-full" style={{ width: `${Math.min(100, projectedEmployability || 0)}%` }} />
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
              <span className="font-semibold text-slate-900">{currentGaps !== null ? currentGaps : 'N/D'}</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-red-500 rounded-full" style={{ width: `${Math.min(100, (currentGaps || 0) / 30 * 100)}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Projected</span>
              <span className="font-semibold text-slate-900">{projectedGaps !== null ? projectedGaps : 'N/D'}</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div className="h-2 bg-amber-500 rounded-full" style={{ width: `${Math.min(100, (projectedGaps || 0) / 30 * 100)}%` }} />
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
