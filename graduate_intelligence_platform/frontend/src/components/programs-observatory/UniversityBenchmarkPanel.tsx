import type { Program, RelatedUniversityProgram } from '../../types/api';

interface UniversityBenchmarkPanelProps {
  selectedProgram: Program | null;
  relatedUniversityPrograms: RelatedUniversityProgram[];
  alignment: number;
}

export function UniversityBenchmarkPanel({
  selectedProgram,
  relatedUniversityPrograms,
  alignment,
}: UniversityBenchmarkPanelProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm p-6 space-y-4">
      <div>
        <h3 className="text-lg font-bold text-slate-900">University Benchmarks</h3>
        <p className="text-sm text-slate-600 mt-1">Comparative analysis across institutions</p>
      </div>

      {selectedProgram ? (
        <div className="space-y-4">
          {/* Current Program Benchmark */}
          <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-600">This Program</p>
                <p className="text-sm font-medium text-slate-900 mt-1">{selectedProgram.nombre_especializacion}</p>
              </div>
              <span className="text-2xl font-bold text-blue-900">{alignment.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${alignment}%` }} />
            </div>
          </div>

          {/* Similar Programs Comparison */}
          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-900">Similar Programs at Other Institutions</p>
            {relatedUniversityPrograms.length > 0 ? (
              <div className="space-y-2">
                {relatedUniversityPrograms.slice(0, 5).map((program, idx) => {
                  const progAlignment = Math.round(Number(program.similitud || 0) * 100);
                  return (
                    <div key={`${program.universidad}-${program.programa}-${idx}`} className="rounded border border-slate-200 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-slate-700">{program.programa}</p>
                        <span className="text-sm font-semibold text-slate-900">{progAlignment}%</span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-1.5">
                        <div className="bg-slate-600 h-1.5 rounded-full" style={{ width: `${progAlignment}%` }} />
                      </div>
                      <p className="text-xs text-slate-500 mt-1">{program.universidad} · {program.ciudad || 'Unknown location'}</p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-slate-600">No comparable programs found</p>
            )}
          </div>

          {/* Benchmark Insights */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 space-y-2">
            <p className="text-xs font-semibold uppercase text-slate-600">Positioning</p>
            <p className="text-sm text-slate-700">
              {alignment >= 75
                ? "Strong market alignment with competitive positioning across peer institutions"
                : alignment >= 50
                  ? "Moderate alignment with opportunities to benchmark against leading programs"
                  : "Developing alignment - strategic learning from peer programs recommended"}
            </p>
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-sm text-slate-600">Select a program to view benchmark comparisons</p>
        </div>
      )}
    </div>
  );
}
