import { AlertCircle, TrendingDown, TrendingUp } from 'lucide-react';
import type { Program } from '../../types/api';

interface ActiveProgramPanelProps {
  program: Program | null;
  alignment: number;
  risk: number;
  employability: number;
  onSelectProgram: (id: string | null) => void;
}

export function ActiveProgramPanel({
  program,
  alignment,
  risk,
  employability,
  onSelectProgram,
}: ActiveProgramPanelProps) {
  if (!program) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 text-center">
        <p className="text-slate-600">Select a program to view active panel</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-2xl font-semibold text-slate-900">{program.nombre_especializacion}</h3>
          <p className="text-sm text-slate-600 mt-1">{program.rol || 'Academic Program'}</p>
        </div>
        <button
          onClick={() => onSelectProgram(null)}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          Change ×
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Alignment Score */}
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase text-blue-700">Alignment</span>
            <TrendingUp size={16} className="text-blue-600" />
          </div>
          <div className="text-3xl font-bold text-blue-900">{alignment.toFixed(1)}%</div>
          <p className="text-xs text-blue-600 mt-2">Market relevance</p>
        </div>

        {/* Risk Score */}
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase text-red-700">Risk</span>
            <AlertCircle size={16} className="text-red-600" />
          </div>
          <div className="text-3xl font-bold text-red-900">{risk.toFixed(1)}%</div>
          <p className="text-xs text-red-600 mt-2">Curriculum gap</p>
        </div>

        {/* Employability */}
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase text-green-700">Employability</span>
            <TrendingUp size={16} className="text-green-600" />
          </div>
          <div className="text-3xl font-bold text-green-900">{employability.toFixed(1)}%</div>
          <p className="text-xs text-green-600 mt-2">Graduate prospects</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="p-3 bg-slate-50 rounded border border-slate-200">
          <p className="text-xs text-slate-600 uppercase font-semibold">Skills Visible</p>
          <p className="text-lg font-semibold text-slate-900 mt-1">{program.total_skills_programa || 0}</p>
        </div>
        <div className="p-3 bg-slate-50 rounded border border-slate-200">
          <p className="text-xs text-slate-600 uppercase font-semibold">Related Jobs</p>
          <p className="text-lg font-semibold text-slate-900 mt-1">{program.total_empleos_relacionados || 0}</p>
        </div>
      </div>
    </div>
  );
}
