import type { Program } from '../../types/api';

interface CurriculumMatchProps {
  program: Program | null;
  programId: number | null;
}

export function CurriculumVsMarketMatch({
  program,
  academicSkills,
  laborSkills,
  gaps,
}: CurriculumMatchProps) {
  if (!program) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 mb-6">Curriculum vs Market Match</h3>

      <div className="grid grid-cols-3 gap-6">
        {/* Academic Skills */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-slate-700">Academic Skills</span>
            <span className="text-sm font-bold text-blue-600">{academicSkills}</span>
          </div>
          <div className="space-y-2">
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500" style={{ width: `${Math.min(100, (academicSkills / 50) * 100)}%` }} />
            </div>
            <p className="text-xs text-slate-600">Defined in curriculum</p>
          </div>
        </div>

        {/* Labor Market Skills */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-slate-700">Labor Market Skills</span>
            <span className="text-sm font-bold text-green-600">{laborSkills}</span>
          </div>
          <div className="space-y-2">
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-green-500" style={{ width: `${Math.min(100, (laborSkills / 50) * 100)}%` }} />
            </div>
            <p className="text-xs text-slate-600">Observed in job market</p>
          </div>
        </div>

        {/* Curriculum Gaps */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-slate-700">Gaps to Address</span>
            <span className="text-sm font-bold text-amber-600">{gaps}</span>
          </div>
          <div className="space-y-2">
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-amber-500" style={{ width: `${Math.min(100, (gaps / 30) * 100)}%` }} />
            </div>
            <p className="text-xs text-slate-600">Missing or outdated</p>
          </div>
        </div>
      </div>

      {/* Detail breakdown */}
      <div className="mt-6 pt-6 border-t border-slate-200">
        <p className="text-sm text-slate-600 mb-4">Coverage Analysis</p>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs uppercase text-slate-500 font-semibold">Coverage Rate</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">
              {laborSkills > 0 ? ((academicSkills / (academicSkills + gaps)) * 100).toFixed(0) : 0}%
            </p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500 font-semibold">Alignment Gap</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{gaps}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500 font-semibold">Market Signal</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{laborSkills}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
