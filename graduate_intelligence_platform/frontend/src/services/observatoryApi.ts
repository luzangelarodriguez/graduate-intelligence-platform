const API_BASE = 'https://graduate-intelligence-platform-production.up.railway.app/api';

export interface DashboardSummary {
  program_id: number;
  program_name: string;
  pertinencia_general: number;
  cobertura_curricular: number;
  empleabilidad_egresados: number;
  market_alignment: number;
  gap_analysis: string;
}

export interface SkillsAnalysis {
  program_id: number;
  market_demanded_skills: Array<{
    skill: string;
    demand_level: 'high' | 'medium' | 'low';
    salary_range: string;
    urgency: number;
  }>;
  program_taught_skills: Array<{
    skill: string;
    proficiency: string;
    courses: number;
  }>;
  skill_gaps: Array<{
    skill: string;
    gap_percentage: number;
    priority: 'urgent' | 'high' | 'medium';
    recommendation: string;
  }>;
  compatible_jobs: Array<{
    role: string;
    alignment_score: number;
    vacancy_count: number;
    avg_salary: string;
  }>;
}

export interface RelatedUniversities {
  program_id: number;
  universities: Array<{
    name: string;
    location: string;
    similar_programs: number;
  }>;
}

class ObservatoryApi {
  async getSummary(programId: number): Promise<DashboardSummary> {
    try {
      const response = await fetch(
        `${API_BASE}/dashboard/summary?program_id=${programId}`
      );
      if (!response.ok) throw new Error('Failed to fetch summary');
      return await response.json();
    } catch (error) {
      console.error('[v0] Error fetching summary:', error);
      throw error;
    }
  }

  async getSkillsAnalysis(programId: number): Promise<SkillsAnalysis> {
    try {
      const response = await fetch(
        `${API_BASE}/dashboard/skills-analysis/${programId}`
      );
      if (!response.ok) throw new Error('Failed to fetch skills analysis');
      return await response.json();
    } catch (error) {
      console.error('[v0] Error fetching skills analysis:', error);
      throw error;
    }
  }

  async getRelatedUniversities(programId: number): Promise<RelatedUniversities> {
    try {
      const response = await fetch(
        `${API_BASE}/programs/related-universities/${programId}`
      );
      if (!response.ok) throw new Error('Failed to fetch universities');
      return await response.json();
    } catch (error) {
      console.error('[v0] Error fetching universities:', error);
      throw error;
    }
  }

  async getAllData(programId: number) {
    console.log('[v0] Fetching all data for program:', programId);
    try {
      const [summary, skills, universities] = await Promise.all([
        this.getSummary(programId),
        this.getSkillsAnalysis(programId),
        this.getRelatedUniversities(programId),
      ]);
      console.log('[v0] All data fetched successfully');
      return { summary, skills, universities };
    } catch (error) {
      console.error('[v0] Error fetching all data:', error);
      throw error;
    }
  }
}

export const observatoryApi = new ObservatoryApi();
