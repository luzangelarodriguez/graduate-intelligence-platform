import { useCallback, useEffect, useState } from 'react';

import {
  getCompanyIntelligence,
  getEmergingSkills,
  getSemanticRoles,
} from '../services/api';
import type {
  CompanyIntelligence,
  EmergingSkill,
  SemanticRole,
} from '../types/api';

interface UseMercadoLaboralResult {
  emergingSkills: EmergingSkill[];
  companies: CompanyIntelligence[];
  roles: SemanticRole[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useMercadoLaboral(): UseMercadoLaboralResult {
  const [emergingSkills, setEmergingSkills] = useState<EmergingSkill[]>([]);
  const [companies, setCompanies] = useState<CompanyIntelligence[]>([]);
  const [roles, setRoles] = useState<SemanticRole[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [skillsRes, companiesRes, rolesRes] = await Promise.allSettled([
        getEmergingSkills({ limit: 50 }),
        getCompanyIntelligence({ limit: 50 }),
        getSemanticRoles({ limit: 50 }),
      ]);

      if (skillsRes.status === 'fulfilled') {
        setEmergingSkills(skillsRes.value.items);
      }
      if (companiesRes.status === 'fulfilled') {
        setCompanies(companiesRes.value.items);
      }
      if (rolesRes.status === 'fulfilled') {
        setRoles(rolesRes.value.items);
      }

      const allFailed = [skillsRes, companiesRes, rolesRes].every(
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
    roles,
    isLoading,
    error,
    refresh: fetchData,
  };
}
