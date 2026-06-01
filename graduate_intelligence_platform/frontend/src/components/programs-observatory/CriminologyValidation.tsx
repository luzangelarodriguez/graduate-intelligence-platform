import type { Program } from '../../types/api';

interface CriminologyValidationProps {
  program: Program | null;
  isCriminologyProgram: boolean;
}

const CRIMINOLOGY_ALLOWED_KEYWORDS = [
  'criminal',
  'criminology',
  'forensic',
  'law',
  'justice',
  'investigation',
  'crime',
  'penology',
  'victimology',
  'criminalistic',
  'sociology',
  'psychology',
  'procedure',
];

const CRIMINOLOGY_FORBIDDEN_KEYWORDS = [
  'python',
  'javascript',
  'sql',
  'database',
  'cloud',
  'api',
  'web development',
  'machine learning',
  'devops',
  'kubernetes',
  'docker',
  'agile',
];

export function CriminologyValidation({ program, isCriminologyProgram }: CriminologyValidationProps) {
  if (!program || !isCriminologyProgram) {
    return null;
  }

  const programName = program.nombre_especializacion?.toLowerCase() || '';
  const allowedFound = CRIMINOLOGY_ALLOWED_KEYWORDS.filter(kw => programName.includes(kw));
  const forbiddenFound = CRIMINOLOGY_FORBIDDEN_KEYWORDS.filter(kw => programName.includes(kw));

  const isValid = allowedFound.length > 0 && forbiddenFound.length === 0;

  return (
    <div className={`rounded-lg border p-6 shadow-sm ${
      isValid ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
    }`}>
      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${isValid ? 'bg-green-600' : 'bg-red-600'}`} />
        <span className={isValid ? 'text-green-900' : 'text-red-900'}>Criminology Program Validation</span>
      </h3>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="text-sm font-semibold mb-3 text-slate-700">Allowed Keywords Found</p>
          <div className="space-y-2">
            {allowedFound.length > 0 ? (
              allowedFound.map((kw) => (
                <div key={kw} className="text-sm p-2 rounded bg-white border border-green-200">
                  <span className="text-green-700 font-medium">✓</span> {kw}
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-600">No allowed keywords detected</p>
            )}
          </div>
        </div>

        <div>
          <p className="text-sm font-semibold mb-3 text-slate-700">Forbidden Keywords Found</p>
          <div className="space-y-2">
            {forbiddenFound.length > 0 ? (
              forbiddenFound.map((kw) => (
                <div key={kw} className="text-sm p-2 rounded bg-white border border-red-200">
                  <span className="text-red-700 font-medium">✗</span> {kw}
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-600">No forbidden keywords detected</p>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-200">
        <p className="text-sm font-semibold mb-2 text-slate-700">Validation Status</p>
        <div className={`text-sm p-3 rounded ${isValid ? 'bg-white border border-green-200' : 'bg-white border border-red-200'}`}>
          {isValid ? (
            <p className="text-green-700">
              <span className="font-semibold">✓ Valid</span> - Program aligns with criminology domain and excludes inappropriate technical terms.
            </p>
          ) : (
            <p className="text-red-700">
              <span className="font-semibold">✗ Invalid</span> - Program contains technical terms that are inappropriate for criminology specialization.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
