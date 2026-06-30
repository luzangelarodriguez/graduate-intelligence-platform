export type ResourceStatus = 'success' | 'empty' | 'error';

export interface ResourceResult<T> {
  status: ResourceStatus;
  data: T | null;
  count: number;
  endpoint: string;
  message: string;
  action: string;
  error?: string;
}

function countRecords(data: unknown) {
  if (Array.isArray(data)) return data.length;
  if (data && typeof data === 'object' && Array.isArray((data as { items?: unknown[] }).items)) {
    return ((data as { items: unknown[] }).items).length;
  }
  return data ? 1 : 0;
}

export async function requestResource<T>(
  endpoint: string,
  loader: () => Promise<T>,
  emptyMessage: string,
  emptyAction: string,
): Promise<ResourceResult<T>> {
  try {
    const data = await loader();
    const count = countRecords(data);
    if (count === 0) {
      return {
        status: 'empty',
        data,
        count,
        endpoint,
        message: emptyMessage,
        action: emptyAction,
      };
    }
    return {
      status: 'success',
      data,
      count,
      endpoint,
      message: 'El endpoint respondió correctamente y entregó registros.',
      action: 'Usar la evidencia disponible para la lectura institucional.',
    };
  } catch (cause) {
    const error = cause instanceof Error ? cause.message : 'Error no identificado al consultar el endpoint.';
    return {
      status: 'error',
      data: null,
      count: 0,
      endpoint,
      message: `No fue posible consultar ${endpoint}.`,
      action: 'Verifique conectividad, disponibilidad del backend y configuración de VITE_API_BASE_URL.',
      error,
    };
  }
}



