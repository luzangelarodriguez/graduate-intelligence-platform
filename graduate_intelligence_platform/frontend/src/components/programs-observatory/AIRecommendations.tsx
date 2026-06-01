interface Recommendation {
  finding: string;
  evidence: string;
  impact: string;
  priority: 'high' | 'medium' | 'low';
}

interface AIRecommendationsProps {
  recommendations: Recommendation[];
  loading?: boolean;
}

export function AIRecommendations({ recommendations, loading = false }: AIRecommendationsProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900 mb-6">AI Recommendations</h3>
        <div className="text-center py-8">
          <div className="inline-block animate-spin">
            <div className="w-6 h-6 border-3 border-slate-200 border-t-slate-900 rounded-full" />
          </div>
          <p className="text-sm text-slate-600 mt-3">Analyzing program recommendations...</p>
        </div>
      </div>
    );
  }

  if (!recommendations.length) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm text-center">
        <p className="text-slate-600">No recommendations available for this program</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 mb-6">AI Recommendations</h3>

      <div className="space-y-4">
        {recommendations.slice(0, 6).map((rec, idx) => {
          const priorityColors = {
            high: 'border-red-200 bg-red-50',
            medium: 'border-amber-200 bg-amber-50',
            low: 'border-blue-200 bg-blue-50',
          };
          const priorityBadgeColors = {
            high: 'bg-red-100 text-red-700',
            medium: 'bg-amber-100 text-amber-700',
            low: 'bg-blue-100 text-blue-700',
          };

          return (
            <div key={idx} className={`rounded-lg border p-4 ${priorityColors[rec.priority]}`}>
              <div className="flex items-start justify-between mb-3">
                <h4 className="font-semibold text-slate-900 flex-1">{rec.finding}</h4>
                <span className={`text-xs font-semibold px-2.5 py-1 rounded whitespace-nowrap ml-2 ${priorityBadgeColors[rec.priority]}`}>
                  {rec.priority.charAt(0).toUpperCase() + rec.priority.slice(1)}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs uppercase font-semibold text-slate-600 mb-1">Evidence</p>
                  <p className="text-slate-700">{rec.evidence}</p>
                </div>
                <div>
                  <p className="text-xs uppercase font-semibold text-slate-600 mb-1">Impact</p>
                  <p className="text-slate-700">{rec.impact}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {recommendations.length > 6 && (
        <p className="text-xs text-slate-600 mt-4 pt-4 border-t border-slate-200">
          Showing 6 of {recommendations.length} recommendations
        </p>
      )}
    </div>
  );
}
