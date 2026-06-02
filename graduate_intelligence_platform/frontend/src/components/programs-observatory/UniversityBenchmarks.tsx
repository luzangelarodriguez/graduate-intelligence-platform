import { Loader2 } from 'lucide-react';
import { useUniversityBenchmarks } from '../../hooks/useUniversityBenchmarks';
import type { RelatedUniversityProgram } from '../../types/api';

interface UniversityBenchmarksProps {
  programId: number | null;
}

export function UniversityBenchmarks({ programId }: UniversityBenchmarksProps) {
  const { programs, isLoading, error } = useUniversityBenchmarks(programId, 10);

  if (!programId) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 text-center">
        <p className="text-slate-600">Select a program to view benchmarks</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 flex items-center justify-center gap-3">
        <Loader2 size={20} className="animate-spin text-blue-600" />
        <p className="text-slate-600">Loading university benchmarks...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="text-red-900 font-semibold">Error loading benchmarks</p>
        <p className="text-sm text-red-700 mt-2">{error.message}</p>
      </div>
    );
  }

  if (!programs || programs.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm text-center">
        <p className="text-slate-600">No comparable programs found in SNIES database</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm overflow-x-auto">
      <h3 className="text-lg font-semibold text-slate-900 mb-6">University Competitor Benchmarks</h3>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-3 px-3 font-semibold text-slate-700">Universidad</th>
            <th className="text-left py-3 px-3 font-semibold text-slate-700">Programa</th>
            <th className="text-left py-3 px-3 font-semibold text-slate-700">Cobertura</th>
            <th className="text-left py-3 px-3 font-semibold text-slate-700">Diferenciador</th>
            <th className="text-center py-3 px-3 font-semibold text-slate-700">Score</th>
          </tr>
        </thead>
        <tbody>
          {programs.slice(0, 8).map((prog: RelatedUniversityProgram, idx: number) => {
            const similarity = prog.similitud ? Math.round(Number(prog.similitud) * 100) : 0;
            return (
              <tr key={`${prog.universidad}-${prog.programa}-${idx}`} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 px-3 text-slate-900 font-medium">{prog.universidad || 'N/D'}</td>
                <td className="py-3 px-3 text-slate-700">{prog.programa || 'N/D'}</td>
                <td className="py-3 px-3 text-slate-600">{prog.ciudad || 'Nacional'} · {prog.modalidad || 'Virtual'}</td>
                <td className="py-3 px-3 text-slate-600">{prog.competidor || 'Comparable offer'}</td>
                <td className="py-3 px-3 text-center">
                  <span className={`inline-flex items-center justify-center w-12 h-8 rounded font-semibold text-sm ${
                    similarity >= 80 ? 'bg-green-100 text-green-700' :
                    similarity >= 60 ? 'bg-blue-100 text-blue-700' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {similarity}%
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {programs.length > 8 && (
        <p className="text-xs text-slate-600 mt-4 pt-4 border-t border-slate-200">
          Showing 8 of {programs.length} comparable programs
        </p>
      )}
    </div>
  );
}
