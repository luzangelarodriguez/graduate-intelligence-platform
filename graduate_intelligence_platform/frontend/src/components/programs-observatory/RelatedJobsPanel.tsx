import type { Match } from '../../types/api';

interface RelatedJobsPanelProps {
  matches: Match[];
}

export function RelatedJobsPanel({ matches }: RelatedJobsPanelProps) {
  if (!matches.length) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm text-center">
        <p className="text-slate-600">No related jobs found in labor market signal</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm overflow-x-auto">
      <h3 className="text-lg font-semibold text-slate-900 mb-6">Related Jobs Panel</h3>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-3 px-3 font-semibold text-slate-700">Cargo</th>
            <th className="text-left py-3 px-3 font-semibold text-slate-700">Empresa</th>
            <th className="text-center py-3 px-3 font-semibold text-slate-700">Skills Match</th>
            <th className="text-center py-3 px-3 font-semibold text-slate-700">Match %</th>
          </tr>
        </thead>
        <tbody>
          {matches.slice(0, 10).map((match, idx) => {
            const matchPercent = Number(match.porcentaje_match || 0);
            return (
              <tr key={`${match.empleo_id}-${idx}`} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 px-3 text-slate-900 font-medium">{match.titulo_empleo}</td>
                <td className="py-3 px-3 text-slate-600">Employer</td>
                <td className="py-3 px-3 text-center text-slate-600">
                  <span className="text-xs bg-slate-100 px-2 py-1 rounded">
                    {match.skills_en_comun} / {match.total_skills_empleo}
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-12 bg-slate-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          matchPercent >= 80 ? 'bg-green-500' :
                          matchPercent >= 60 ? 'bg-blue-500' :
                          'bg-amber-500'
                        }`}
                        style={{ width: `${Math.min(100, matchPercent)}%` }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-slate-900 w-8 text-right">{matchPercent.toFixed(0)}%</span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {matches.length > 10 && (
        <p className="text-xs text-slate-600 mt-4 pt-4 border-t border-slate-200">
          Showing 10 of {matches.length} related job positions
        </p>
      )}
    </div>
  );
}
