export function LoadingState({ label = 'Cargando inteligencia operacional...' }: { label?: string }) {
  return (
    <div className="grid min-h-[360px] place-items-center rounded-lg border border-line bg-white">
      <div className="text-center">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-line border-t-brand" />
        <p className="mt-4 text-sm font-semibold text-muted">{label}</p>
      </div>
    </div>
  );
}
