interface KpiCardProps {
  label: string;
  value: string | number;
  detail: string;
  tone?: 'blue' | 'green' | 'amber' | 'dark';
}

const toneClass = {
  blue: 'from-blue-50 to-white text-brand',
  green: 'from-emerald-50 to-white text-emerald',
  amber: 'from-amber-50 to-white text-amber',
  dark: 'from-slate-100 to-white text-ink',
};

export function KpiCard({ label, value, detail, tone = 'blue' }: KpiCardProps) {
  return (
    <article className={`panel bg-gradient-to-br ${toneClass[tone]}`}>
      <p className="text-xs font-semibold uppercase text-muted">{label}</p>
      <strong className="mt-4 block text-3xl font900 tracking-normal">{value}</strong>
      <span className="mt-3 block text-sm leading-6 text-muted">{detail}</span>
    </article>
  );
}
