import { useCallback, useEffect, useState } from 'react';
import {
  Building2,
  Cpu,
  Cloud,
  BarChart3,
  TrendingUp,
  Zap,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ScatterChart,
  Scatter,
  ZAxis,
  Legend,
} from 'recharts';

import {
  InsightCard,
  NarrativeSection,
  StoryMetric,
  NarrativeSkeleton,
} from '../components/narrative/NarrativeComponents';
import {
  getCompanyIntelligence,
  getEmergingSkills,
  getCareerPaths,
} from '../services/api';
import type {
  CompanyIntelligence,
  EmergingSkill,
  CareerPath,
} from '../types/api';

interface MarketData {
  companies: CompanyIntelligence[];
  skills: EmergingSkill[];
  careerPaths: CareerPath[];
}

export default function MarketSignalsPage() {
  const [data, setData] = useState<MarketData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [companiesRes, skillsRes, careerRes] = await Promise.allSettled([
        getCompanyIntelligence({ limit: 100 }),
        getEmergingSkills({ limit: 100 }),
        getCareerPaths({ limit: 100 }),
      ]);

      setData({
        companies: companiesRes.status === 'fulfilled' ? companiesRes.value.items : [],
        skills: skillsRes.status === 'fulfilled' ? skillsRes.value.items : [],
        careerPaths: careerRes.status === 'fulfilled' ? careerRes.value.items : [],
      });
    } catch (err) {
      setError('Error al cargar senales del mercado.');
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

  const { companies, skills, careerPaths } = data;

  // Calculate metrics
  const avgAIAdoption = companies.length > 0
    ? Math.round(companies.reduce((sum, c) => sum + (parseFloat(c.ai_adoption_score) || 0), 0) / companies.length * 100)
    : 0;
  const avgCloudMaturity = companies.length > 0
    ? Math.round(companies.reduce((sum, c) => sum + (parseFloat(c.cloud_maturity_score) || 0), 0) / companies.length * 100)
    : 0;
  const avgBIMaturity = companies.length > 0
    ? Math.round(companies.reduce((sum, c) => sum + (parseFloat(c.bi_maturity_score) || 0), 0) / companies.length * 100)
    : 0;

  // Top hiring companies
  const topHiringCompanies = [...companies]
    .sort((a, b) => (parseFloat(b.hiring_velocity) || 0) - (parseFloat(a.hiring_velocity) || 0))
    .slice(0, 8);

  // Technology adoption scatter data
  const techScatterData = companies.map(c => ({
    name: c.company,
    x: Math.round((parseFloat(c.ai_adoption_score) || 0) * 100),
    y: Math.round((parseFloat(c.cloud_maturity_score) || 0) * 100),
    z: Math.round((parseFloat(c.hiring_velocity) || 0) * 100),
  }));

  // Stack distribution
  const stackCounts = companies.reduce((acc, c) => {
    const stack = c.dominant_stack || 'Otro';
    acc[stack] = (acc[stack] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const stackData = Object.entries(stackCounts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  // Generate narrative
  const generateInsight = () => {
    const highAICompanies = companies.filter(c => (parseFloat(c.ai_adoption_score) || 0) > 0.5).length;
    if (avgAIAdoption > 30) {
      return `El ${avgAIAdoption}% de las empresas analizadas muestran adopcion de IA, con ${highAICompanies} organizaciones liderando la transformacion digital.`;
    } else {
      return `La adopcion de IA en el mercado es del ${avgAIAdoption}%. Existe oportunidad de diferenciacion para graduados con competencias en tecnologias emergentes.`;
    }
  };

  // Hiring chart data
  const hiringChartData = topHiringCompanies.map(c => ({
    name: c.company.substring(0, 15),
    hiring: Math.round((parseFloat(c.hiring_velocity) || 0) * 100),
    ai: Math.round((parseFloat(c.ai_adoption_score) || 0) * 100),
  }));

  return (
    <div className="space-y-8">
      {/* Main Insight */}
      <InsightCard
        headline={generateInsight()}
        body={`Se analizaron ${companies.length} empresas y ${careerPaths.length} trayectorias profesionales para identificar tendencias del mercado laboral.`}
        variant="default"
        metric={{
          value: companies.length,
          label: 'Empresas Analizadas',
        }}
      />

      {/* Market KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StoryMetric
          icon={<Building2 className="w-5 h-5 text-primary" />}
          value={companies.length}
          label="Empresas"
          context="Fuentes de demanda"
        />
        <StoryMetric
          icon={<Cpu className="w-5 h-5 text-primary" />}
          value={`${avgAIAdoption}%`}
          label="Adopcion IA"
          context="Promedio empresas"
        />
        <StoryMetric
          icon={<Cloud className="w-5 h-5 text-primary" />}
          value={`${avgCloudMaturity}%`}
          label="Madurez Cloud"
          context="Promedio empresas"
        />
        <StoryMetric
          icon={<BarChart3 className="w-5 h-5 text-primary" />}
          value={`${avgBIMaturity}%`}
          label="Madurez BI"
          context="Promedio empresas"
        />
        <StoryMetric
          icon={<TrendingUp className="w-5 h-5 text-primary" />}
          value={careerPaths.length}
          label="Trayectorias"
          context="Rutas de carrera"
        />
        <StoryMetric
          icon={<Zap className="w-5 h-5 text-primary" />}
          value={skills.length || 0}
          label="Skills"
          context="Emergentes detectadas"
        />
      </div>

      {/* Hiring Activity */}
      <NarrativeSection
        title="Actividad de Contratacion por Empresa"
        subtitle="Velocidad de contratacion vs adopcion de IA"
      >
        <div className="bg-white rounded-lg border border-line p-5">
          {hiringChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={hiringChartData} margin={{ left: 10, right: 20, bottom: 60 }}>
                <XAxis 
                  dataKey="name" 
                  angle={-45} 
                  textAnchor="end" 
                  height={80} 
                  fontSize={11} 
                  tick={{ fill: '#64748B' }}
                />
                <YAxis tickFormatter={v => `${v}%`} fontSize={12} />
                <Tooltip formatter={(v: number) => [`${v}%`]} />
                <Legend wrapperStyle={{ paddingTop: 20 }} />
                <Bar dataKey="hiring" name="Contratacion" fill="#003A70" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ai" name="Adopcion IA" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-muted py-12">Sin datos de empresas</p>
          )}
        </div>
      </NarrativeSection>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Tech Maturity Quadrant */}
        <NarrativeSection
          title="Madurez Tecnologica"
          subtitle="Adopcion IA vs Cloud (tamano = velocidad contratacion)"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {techScatterData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <XAxis 
                    type="number" 
                    dataKey="x" 
                    name="Adopcion IA" 
                    domain={[0, 100]}
                    tickFormatter={v => `${v}%`}
                    fontSize={11}
                  />
                  <YAxis 
                    type="number" 
                    dataKey="y" 
                    name="Cloud" 
                    domain={[0, 100]}
                    tickFormatter={v => `${v}%`}
                    fontSize={11}
                  />
                  <ZAxis type="number" dataKey="z" range={[50, 400]} />
                  <Tooltip 
                    formatter={(value: number, name: string) => [`${value}%`, name]}
                    labelFormatter={(label) => techScatterData.find(d => d.x === label)?.name || ''}
                  />
                  <Scatter 
                    data={techScatterData} 
                    fill="#003A70"
                    fillOpacity={0.6}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-muted py-12">Sin datos de madurez</p>
            )}
          </div>
        </NarrativeSection>

        {/* Technology Stack Distribution */}
        <NarrativeSection
          title="Stacks Tecnologicos Dominantes"
          subtitle="Distribucion de tecnologias en empresas analizadas"
        >
          <div className="bg-white rounded-lg border border-line p-5">
            {stackData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={stackData} layout="vertical" margin={{ left: 80 }}>
                  <XAxis type="number" fontSize={12} />
                  <YAxis type="category" dataKey="name" fontSize={11} tick={{ fill: '#64748B' }} />
                  <Tooltip />
                  <Bar dataKey="value" name="Empresas" fill="#003A70" radius={[0, 4, 4, 0]}>
                    {stackData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? '#003A70' : '#64748B'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-muted py-12">Sin datos de stacks</p>
            )}
          </div>
        </NarrativeSection>
      </div>

      {/* Company Intelligence Table */}
      <NarrativeSection
        title="Inteligencia de Empresas"
        subtitle="Detalle de madurez tecnologica y actividad de contratacion"
      >
        <div className="bg-white rounded-lg border border-line overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-subtle">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Empresa</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Contratacion</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">IA</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">Cloud</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted uppercase">BI</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Stack</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase">Cluster</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {companies.slice(0, 12).map((company, idx) => (
                  <tr key={idx} className="hover:bg-subtle/50">
                    <td className="px-4 py-3 text-sm font-medium text-foreground">
                      {company.company}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-sm font-medium text-foreground">
                        {Math.round((parseFloat(company.hiring_velocity) || 0) * 100)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-sm font-medium ${
                        (parseFloat(company.ai_adoption_score) || 0) > 0.5 ? 'text-success' : 'text-foreground'
                      }`}>
                        {Math.round((parseFloat(company.ai_adoption_score) || 0) * 100)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-sm font-medium text-foreground">
                        {Math.round((parseFloat(company.cloud_maturity_score) || 0) * 100)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-sm font-medium text-foreground">
                        {Math.round((parseFloat(company.bi_maturity_score) || 0) * 100)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted">
                      {company.dominant_stack || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted">
                      {company.dominant_cluster || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </NarrativeSection>
    </div>
  );
}
