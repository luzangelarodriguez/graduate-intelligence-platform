import type { Program } from '../../types/api';

interface MicrocurriculumModule {
  id: string;
  name: string;
  competencies: string[];
  skillsCovered: number;
  skillsNeeded: number;
  gapPercentage: number;
}

interface MicrocurriculumModulesProps {
  program: Program | null;
  modules?: MicrocurriculumModule[];
}

export function MicrocurriculumModules({ program, modules = [] }: MicrocurriculumModulesProps) {
  if (!program) return null;

  // Default modules based on program structure if not provided
  const defaultModules: MicrocurriculumModule[] = [
    {
      id: '1',
      name: 'Core Fundamentals',
      competencies: ['Problem Solving', 'Critical Thinking', 'Communication'],
      skillsCovered: 12,
      skillsNeeded: 15,
      gapPercentage: 20,
    },
    {
      id: '2',
      name: 'Technical Skills',
      competencies: ['Data Analysis', 'Programming', 'Database Management'],
      skillsCovered: 8,
      skillsNeeded: 12,
      gapPercentage: 33,
    },
    {
      id: '3',
      name: 'Professional Development',
      competencies: ['Leadership', 'Project Management', 'Teamwork'],
      skillsCovered: 6,
      skillsNeeded: 8,
      gapPercentage: 25,
    },
  ];

  const displayModules = modules.length > 0 ? modules : defaultModules;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 mb-6">Microcurriculum Modules</h3>

      <div className="space-y-4">
        {displayModules.map((module) => (
          <div key={module.id} className="rounded-lg border border-slate-200 p-4 hover:shadow-sm transition">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="font-semibold text-slate-900">{module.name}</h4>
                <div className="flex flex-wrap gap-2 mt-2">
                  {module.competencies.map((comp) => (
                    <span key={comp} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      {comp}
                    </span>
                  ))}
                </div>
              </div>
              <span className={`text-sm font-semibold px-3 py-1 rounded ${
                module.gapPercentage <= 15 ? 'bg-green-100 text-green-700' :
                module.gapPercentage <= 30 ? 'bg-blue-100 text-blue-700' :
                'bg-amber-100 text-amber-700'
              }`}>
                {module.gapPercentage}% gap
              </span>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-slate-600">Skills Coverage</span>
                  <span className="text-xs font-semibold text-slate-900">{module.skillsCovered} / {module.skillsNeeded}</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="h-2 bg-green-500 rounded-full transition-all"
                    style={{ width: `${(module.skillsCovered / module.skillsNeeded) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-6 border-t border-slate-200">
        <p className="text-sm text-slate-600 mb-4">Module Summary</p>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs uppercase text-slate-500 font-semibold">Total Coverage</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">
              {displayModules.length > 0 
                ? ((displayModules.reduce((s, m) => s + m.skillsCovered, 0) / 
                   displayModules.reduce((s, m) => s + m.skillsNeeded, 0)) * 100).toFixed(0)
                : 0}%
            </p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500 font-semibold">Modules</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{displayModules.length}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500 font-semibold">Avg Gap</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">
              {(displayModules.reduce((s, m) => s + m.gapPercentage, 0) / displayModules.length).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
