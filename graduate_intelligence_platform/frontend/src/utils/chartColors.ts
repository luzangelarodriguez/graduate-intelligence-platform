const BLUE_STOPS = [
  '#0B1730', '#14275A', '#1E3A8A', '#2563EB',
  '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE',
];

function interpolateHex(a: string, b: string, t: number): string {
  const r1 = parseInt(a.slice(1, 3), 16), g1 = parseInt(a.slice(3, 5), 16), b1 = parseInt(a.slice(5, 7), 16);
  const r2 = parseInt(b.slice(1, 3), 16), g2 = parseInt(b.slice(3, 5), 16), b2 = parseInt(b.slice(5, 7), 16);
  const r  = Math.round(r1 + (r2 - r1) * t).toString(16).padStart(2, '0');
  const g  = Math.round(g1 + (g2 - g1) * t).toString(16).padStart(2, '0');
  const bl = Math.round(b1 + (b2 - b1) * t).toString(16).padStart(2, '0');
  return `#${r}${g}${bl}`;
}

export function blueGradient(n: number): string[] {
  if (n <= 0) return [];
  if (n === 1) return [BLUE_STOPS[0]];
  if (n <= BLUE_STOPS.length) return BLUE_STOPS.slice(0, n);
  return Array.from({ length: n }, (_, i) => {
    const t  = i / (n - 1);
    const fi = t * (BLUE_STOPS.length - 1);
    const lo = Math.floor(fi);
    const hi = Math.min(lo + 1, BLUE_STOPS.length - 1);
    return interpolateHex(BLUE_STOPS[lo], BLUE_STOPS[hi], fi - lo);
  });
}
