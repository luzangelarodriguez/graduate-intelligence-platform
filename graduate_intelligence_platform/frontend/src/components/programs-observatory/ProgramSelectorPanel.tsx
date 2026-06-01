import { ChevronDown, Search } from 'lucide-react';
import type { Program } from '../../types/api';

interface ProgramSelectorPanelProps {
  programs: Program[];
  selectedProgramId: number | null;
  onSelectProgram: (programId: number) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export function ProgramSelectorPanel({
  programs,
  selectedProgramId,
  onSelectProgram,
  searchQuery,
  onSearchChange,
}: ProgramSelectorPanelProps) {
  const filteredPrograms = programs.filter((p) =>
    p.nombre_especializacion.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Search Header */}
      <div className="border-b border-slate-200 p-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search programs..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Programs List */}
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-slate-200">
          {filteredPrograms.map((program) => (
            <button
              key={program.especializacion_id}
              onClick={() => onSelectProgram(program.especializacion_id)}
              className={`w-full text-left px-4 py-3 transition-colors ${
                selectedProgramId === program.especializacion_id
                  ? 'bg-blue-50 border-l-4 border-blue-500'
                  : 'hover:bg-slate-50'
              }`}
            >
              <div className="font-medium text-sm text-slate-900">{program.nombre_especializacion}</div>
              <div className="text-xs text-slate-600 mt-1">{program.rol || 'Academic Area'}</div>
            </button>
          ))}
        </div>

        {filteredPrograms.length === 0 && (
          <div className="p-4 text-center text-sm text-slate-600">No programs found</div>
        )}
      </div>
    </div>
  );
}
