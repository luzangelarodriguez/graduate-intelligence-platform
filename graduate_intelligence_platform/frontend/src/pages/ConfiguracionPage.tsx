import { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Database,
  RefreshCw,
  Server,
  Settings,
  XCircle,
} from 'lucide-react';

import {
  EmptyState,
  KpiCard,
  KpiGrid,
  SectionHeader,
  StatusBadge,
} from '../components/ui';
import { getObservatoryHealth } from '../services/api';
import type { HealthResponse } from '../types/api';

export function ConfiguracionPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getObservatoryHealth();
      setHealth(response);
    } catch (err) {
      setError('No se pudo conectar con el servidor del observatorio.');
      console.error('[v0] Health check error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'No configurada';

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Configuracion</h1>
        <p className="page-subtitle text-balance">
          Estado del sistema, conexion con el observatorio y preferencias de la plataforma.
        </p>
      </div>

      {/* System Status */}
      <section className="exec-card p-5">
        <div className="flex items-start justify-between gap-4 mb-5">
          <SectionHeader
            title="Estado del Sistema"
            description="Conectividad y salud del observatorio"
          />
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchHealth}
            disabled={isLoading}
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            Verificar
          </button>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-4 bg-canvas rounded animate-pulse">
                <div className="h-4 bg-line rounded w-1/2 mb-2" />
                <div className="h-6 bg-line rounded w-3/4" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="notice notice-danger flex items-center gap-3">
            <XCircle size={18} />
            <span>{error}</span>
          </div>
        ) : health ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-canvas rounded">
              <div className="flex items-center gap-2 mb-2">
                <Server size={16} className="text-muted" />
                <span className="text-xs font-semibold text-muted uppercase">API Status</span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`status-dot ${health.status === 'ok' ? 'online' : 'warning'}`}
                />
                <span className="font-semibold text-ink">
                  {health.status === 'ok' ? 'Operativo' : 'Degradado'}
                </span>
              </div>
            </div>
            <div className="p-4 bg-canvas rounded">
              <div className="flex items-center gap-2 mb-2">
                <Database size={16} className="text-muted" />
                <span className="text-xs font-semibold text-muted uppercase">Base de Datos</span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`status-dot ${
                    health.database === 'connected' ? 'online' : 'offline'
                  }`}
                />
                <span className="font-semibold text-ink">
                  {health.database === 'connected' ? 'Conectada' : 'Desconectada'}
                </span>
              </div>
            </div>
            <div className="p-4 bg-canvas rounded">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 size={16} className="text-muted" />
                <span className="text-xs font-semibold text-muted uppercase">Ultima Verificacion</span>
              </div>
              <span className="font-semibold text-ink">
                {new Date(health.timestamp).toLocaleString('es-CO', {
                  dateStyle: 'short',
                  timeStyle: 'short',
                })}
              </span>
            </div>
          </div>
        ) : null}

        {/* Health Checks */}
        {health?.checks && Object.keys(health.checks).length > 0 && (
          <div className="mt-5 pt-5 border-t border-line">
            <h4 className="text-sm font-semibold text-ink mb-3">Verificaciones del Sistema</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Object.entries(health.checks).map(([key, value]) => (
                <div
                  key={key}
                  className={`p-3 rounded border ${
                    value ? 'border-success-light bg-success-light' : 'border-danger-light bg-danger-light'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {value ? (
                      <CheckCircle2 size={14} className="text-success" />
                    ) : (
                      <XCircle size={14} className="text-danger" />
                    )}
                    <span className={`text-sm font-medium ${value ? 'text-success' : 'text-danger'}`}>
                      {key}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Observatory Freshness */}
        {health?.observatory_freshness && (
          <div className="mt-5 pt-5 border-t border-line">
            <h4 className="text-sm font-semibold text-ink mb-3">Frescura de Datos</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 bg-canvas rounded">
                <span className="text-xs font-semibold text-muted uppercase block mb-1">
                  Ultima Actualizacion
                </span>
                <span className="font-semibold text-ink">
                  {health.observatory_freshness.last_update
                    ? new Date(health.observatory_freshness.last_update).toLocaleDateString('es-CO', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      })
                    : 'No disponible'}
                </span>
              </div>
              <div className="p-4 bg-canvas rounded">
                <span className="text-xs font-semibold text-muted uppercase block mb-1">
                  Registros Procesados
                </span>
                <span className="font-semibold text-ink">
                  {health.observatory_freshness.records_count?.toLocaleString() ?? 'N/A'}
                </span>
              </div>
              <div className="p-4 bg-canvas rounded">
                <span className="text-xs font-semibold text-muted uppercase block mb-1">
                  Estado de Datos
                </span>
                <StatusBadge
                  status={health.observatory_freshness.status === 'fresh' ? 'success' : 'warning'}
                  label={health.observatory_freshness.status === 'fresh' ? 'Actualizado' : 'Desactualizado'}
                  dot
                />
              </div>
            </div>
          </div>
        )}
      </section>

      {/* API Configuration */}
      <section className="exec-card p-5">
        <SectionHeader
          title="Configuracion de API"
          description="Parametros de conexion con el backend del observatorio"
        />
        <div className="space-y-4">
          <div className="p-4 bg-canvas rounded">
            <span className="text-xs font-semibold text-muted uppercase block mb-1">
              URL Base de API
            </span>
            <code className="text-sm font-mono text-ink bg-line px-2 py-1 rounded">
              {apiBaseUrl}
            </code>
          </div>
          <div className="notice notice-info">
            <span className="font-semibold">Nota:</span> La URL de la API se configura mediante la
            variable de entorno <code className="bg-accent/10 px-1 rounded">VITE_API_BASE_URL</code>.
          </div>
        </div>
      </section>

      {/* Platform Info */}
      <section className="exec-card p-5">
        <SectionHeader
          title="Acerca de la Plataforma"
          description="Informacion del Observatorio Curricular"
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 bg-canvas rounded">
            <span className="text-xs font-semibold text-muted uppercase block mb-1">
              Nombre
            </span>
            <span className="font-semibold text-ink">
              Observatorio Curricular UNIR Colombia
            </span>
          </div>
          <div className="p-4 bg-canvas rounded">
            <span className="text-xs font-semibold text-muted uppercase block mb-1">
              Version
            </span>
            <span className="font-semibold text-ink">2.0.0</span>
          </div>
          <div className="p-4 bg-canvas rounded sm:col-span-2">
            <span className="text-xs font-semibold text-muted uppercase block mb-1">
              Descripcion
            </span>
            <p className="text-sm text-ink leading-relaxed">
              Plataforma de inteligencia curricular para el analisis de pertinencia academica,
              demanda laboral y brechas de habilidades. Desarrollada para orientar decisiones
              academicas en UNIR Colombia.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
