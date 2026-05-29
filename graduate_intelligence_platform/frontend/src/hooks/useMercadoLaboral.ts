import { useCallback, useEffect, useState } from 'react';

import {
  getCareerPaths,
  getCompanyIntelligence,
  getEmergingSkills,
} from '../services/api';
import type {
  CareerPath,
  CompanyIntelligence,
  EmergingSkill,
} from '../types/api';

interface UseMercadoLaboralResult {
  emergingSkills: EmergingSkill[];
  companies: CompanyIntelligence[];
  careerPaths: CareerPath[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useMercadoLaboral(): UseMercadoLaboralResult {
  const [emergingSkills, setEmergingSkills] = useState<EmergingSkill[]>([]);
  const [companies, setCompanies] = useState<CompanyIntelligence[]>([]);
  const [careerPaths, setCareerPaths] = useState<CareerPath[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [skillsRes, companiesRes, careerRes] = await Promise.allSettled([
        getEmergingSkills({ limit: 50 }),
        getCompanyIntelligence({ limit: 50 }),
        getCareerPaths({ limit: 50 }),
      ]);

      if (skillsRes.status === 'fulfilled') {
        setEmergingSkills(skillsRes.value.items);
      }
      if (companiesRes.status === 'fulfilled') {
        setCompanies(companiesRes.value.items);
      }
      if (careerRes.status === 'fulfilled') {
        setCareerPaths(careerRes.value.items);
      }

      const allFailed = [skillsRes, companiesRes, careerRes].every(
        (r) => r.status === 'rejected'
      );
      if (allFailed) {
        setError('No se pudo conectar con el observatorio de mercado laboral.');
      }
    } catch (err) {
      setError('Error al cargar los datos del mercado laboral.');
      console.error('[v0] Mercado laboral fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    emergingSkills,
    companies,
    careerPaths,
    isLoading,
    error,
    refresh: fetchData,
  };
}
