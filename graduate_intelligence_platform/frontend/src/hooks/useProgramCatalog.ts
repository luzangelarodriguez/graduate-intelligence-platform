import { useEffect, useState } from 'react';

import { getProgramas } from '../services/api';
import type { Program } from '../types/api';

interface ProgramCatalogState {
  programs: Program[];
  isLoading: boolean;
  error: string | null;
}

export function useProgramCatalog(limit = 100): ProgramCatalogState {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setIsLoading(true);
        const payload = await getProgramas(limit);
        if (cancelled) return;
        setPrograms(payload.items || []);
        setError(null);
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : 'No fue posible cargar el selector de programas.');
          setPrograms([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [limit]);

  return { programs, isLoading, error };
}
