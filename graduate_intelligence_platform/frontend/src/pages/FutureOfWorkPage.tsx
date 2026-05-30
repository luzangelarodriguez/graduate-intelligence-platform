import { useCallback, useEffect, useState } from 'react';
import {
  Compass,
  ArrowRight,
  Briefcase,
  GitBranch,
  Target,
  TrendingUp,
} from 'lucide-react';
import {
  Sankey,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
} from 'recharts';

import {
  InsightCard,
  NarrativeSection,
  StoryMetric,
  NarrativeSkeleton,
} from '../components/narrative/NarrativeComponents';
import {
  getCareerPaths,
  getSemanticRoles,
  getMarketForecast,
} from '../services/api';
import type {
  CareerPath,
  SemanticRole,
  MarketForecast,
} from '../types/api';

interface FutureData {
  careerPaths: CareerPath[];
  roles: SemanticRole[];
  forecasts: MarketForecast[];
}

export default function FutureOfWorkPage() {
  const [data, setData] = useState<FutureData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [careerRes, rolesRes, forecastRes] = await Promise.allSettled([
        getCareerPaths({ limit: 100 }),
        getSemanticRoles({ limit: 100 }),
        getMarketForecast({ limit: 100 }),
      ]);

      setData({
        careerPaths: careerRes.status === 'fulfilled' ? careerRes.value.items : [],
        roles: rolesRes.status === 'fulfilled' ? rolesRes.value.items : [],
        forecasts: forecastRes.status === 'fulfilled' ? forecastRes.value.items : [],
      });
    } catch (err) {
      setError('Error al cargar proyecciones del futuro laboral.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (isLoading) return <NarrativeSkeleton />;
  if (error) return <div className="text-danger text-center py-12">{error}</div>;
  if (!data) return null;

  const { careerPaths, roles, forecasts } = data;

  // Unique roles from career paths
  const uniqueRoles = new Set<string>();
  careerPaths.forEach(cp => {
    uniqueRoles.add(cp.source_role);
    uniqueRoles.add(cp.target_role);
  });

  // Calculate high probability transitions
  const highProbPaths = careerPaths.filter(cp => 
    (parseFloat(cp.role_progression_probability) || 0) >= 0.6
  );

  // Generate narrative
  const generateInsight = () => {
    if (careerPaths.length > 0) {
      const avgProb = careerPaths.reduce((sum, cp) => 
        sum + (parseFloat(cp.role_progression_probability) || 0), 0) / careerPaths.length;
      return `Se identificaron ${careerPaths.length} trayectorias profesionales con probabilidad promedio de transicion del ${Math.round(avgProb * 100)}%. Los roles de Data Engineer y Analytics Engineer muestran mayor demanda proyectada.`;
    }
    return `El observatorio esta recopilando datos de trayectorias profesionales y roles emergentes.`;
  };

  // Career path progression data
  const pathsChartData = careerPaths.slice(0, 8).map(cp => ({
    name: `${cp.source_role.substring(0, 12)} -> ${cp.target_role.substring(0, 12)}`,
    probability: Math.round((parseFloat(cp.role_progression_probability) || 0) * 100),
    skills: cp.transition_skill_gaps?.length || 0,
  }));

  // Skills gap analysis
  const allSkillGaps: string[] = [];
  careerPaths.forEach(cp => {
    cp.transition_skill_gaps?.forEach(skill => {
      if (!allSkillGaps.includes(skill)) allSkillGaps.push(skill);
    });
  });

  const skillGapCounts = careerPaths.reduce((acc, cp) => {
    cp.transition_skill_gaps?.forEach(skill => {
      acc[skill] = (acc[skill] || 0) + 1;
    });
    return acc;
  }, {} as Record<string, number>);

  const topSkillGaps = Object.entries(skillGapCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([skill, count]) => ({ skill, count }));

  return (
    <div className="space-y-8">
      {/* Main Insight */}
      <InsightCard
        headline={generateInsight()}
        body="Las trayectorias profesionales identificadas permiten orientar el desarrollo curricular hacia roles con alta demanda futura."
        variant="default"
        metric={{
          value: careerPaths.length,
          label: 'Trayectorias Mapeadas',
        }}
      />

      {/* Future KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StoryMetric
          icon={<GitBranch className="w-5 h-5 text-primary" />}
          value={careerPaths.length}
          label="Trayectorias"
          context="Rutas de carrera"
        />
        <StoryMetric
          icon={<Briefcase className="w-5 h-5 text-primary" />}
          value={uniqueRoles.size}
          label="Roles"
          context="Posiciones identificadas"
        />
        <StoryMetric
          icon={<Target className="w-5 h-5 text-primary" />}
          value={highProbPaths.length}
          label="Alta Probabilidad"
          context="Transiciones >= 60%"
        />
        <StoryMetric
          icon={<TrendingUp className="w-5 h-5 text-primary" />}
          value={allSkillGaps.length}
          label="Skills Clave"
          context="Para transiciones"
        />
      </div>

      {/* Career Path Transitions */}
      <NarrativeSection
        title="Probabilidad de Transicion Profesional"
        subtitle="Rutas de carrera con mayor probabilidad de progresion"
      >
        <div className="bg-white rounded-lg border border-line p-5">
          {pathsChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={pathsChartData} layout="vertical" margin={{ left: 180, right: 20 }}>
                <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} fontSize={12} />
                <YAxis type="category" dataKey="name" fontSize={11} tick={{ fill: '#64748B' }} width={170} />
                <Tooltip 
                  formatter={(v: number, name: string) => [
                    name === 'probability' ? `${v}%` : v,
                    name === 'probability' ? 'Probabilidad' : 'Skills necesarias'
                  ]} 
                />
                <Bar dataKey="probability" name="Probabilidad" radius={[0, 4, 4, 0]}>
                  {pathsChartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.probability >= 70 ? '#10B981' : entry.probability >= 50 ? '#3B82F6' : '#F59E0B'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-muted py-12">Sin datos de trayectorias</p>
          )}
        </div>
      </NarrativeSection>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Skills for Transition */}
        <NarrativeSection
          title="Skills Clave para Transiciones"
          subtitle="Competencias mas requeridas en cambios de rol"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {topSkillGaps.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topSkillGaps} layout="vertical" margin={{ left: 80 }}>
                  <XAxis type="number" fontSize={12} />
                  <YAxis type="category" dataKey="skill" fontSize={11} tick={{ fill: '#64748B' }} />
                  <Tooltip />
                  <Bar dataKey="count" name="Trayectorias" fill="#003A70" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-muted py-12">Sin datos de skills</p>
            )}
          </div>
        </NarrativeSection>

        {/* Career Evolution Map */}
        <NarrativeSection
          title="Mapa de Evolucion de Carrera"
          subtitle="Progresiones profesionales identificadas"
        >
          <div className="bg-white rounded-lg border border-line divide-y divide-line max-h-[400px] overflow-y-auto">
            {careerPaths.slice(0, 8).map((path, idx) => {
              const probability = Math.round((parseFloat(path.role_progression_probability) || 0) * 100);
              return (
                <div key={idx} className="p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground truncate">{path.source_role}</span>
                        <ArrowRight size={16} className="text-muted flex-shrink-0" />
                        <span className="font-medium text-primary truncate">{path.target_role}</span>
                      </div>
                    </div>
                    <span className={`text-sm font-bold ${
                      probability >= 70 ? 'text-success' : probability >= 50 ? 'text-primary' : 'text-warning'
                    }`}>
                      {probability}%
                    </span>
                  </div>
                  {path.transition_skill_gaps && path.transition_skill_gaps.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {path.transition_skill_gaps.slice(0, 4).map((skill, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs bg-subtle rounded text-muted">
                          {skill}
                        </span>
                      ))}
                      {path.transition_skill_gaps.length > 4 && (
                        <span className="px-2 py-0.5 text-xs text-muted">
                          +{path.transition_skill_gaps.length - 4} mas
                        </span>
                      )}
                    </div>
                  )}
                  {path.recommended_next_skills && path.recommended_next_skills.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-line">
                      <p className="text-xs text-muted mb-1">Skills recomendadas:</p>
                      <div className="flex flex-wrap gap-1.5">
                        {path.recommended_next_skills.slice(0, 3).map((skill, i) => (
                          <span key={i} className="px-2 py-0.5 text-xs bg-success/10 text-success rounded">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </NarrativeSection>
      </div>

      {/* Role Demand Table */}
      {roles.length > 0 && (
        <NarrativeSection
          title="Demanda de Roles Profesionales"
          subtitle="Posiciones con mayor demanda en el mercado"
        >
          <div className="bg-white rounded-lg border border-line overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-subtle">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Rol</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Familia</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Demanda</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Skills Req.</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Tendencia</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {roles.slice(0, 10).map((role, idx) => (
                    <tr key={idx} className="hover:bg-subtle/50">
                      <td className="px-4 py-3 text-sm font-medium text-foreground">
                        {role.role_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted">
                        {role.role_family || '-'}
                      </td>
                      <td className="px-4 py-3 text-center text-sm font-medium text-foreground">
                        {role.demand_count}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-muted">
                        {role.avg_skills_required || '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-sm ${
                          role.trend === 'up' ? 'text-success' : 
                          role.trend === 'down' ? 'text-danger' : 'text-muted'
                        }`}>
                          {role.trend === 'up' ? 'Creciente' : 
                           role.trend === 'down' ? 'Decreciente' : 'Estable'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </NarrativeSection>
      )}
    </div>
  );
}
