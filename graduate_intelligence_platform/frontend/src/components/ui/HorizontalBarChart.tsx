interface HorizontalBarChartProps {
  data: { label: string; value: number; maxValue?: number }[];
  maxValue?: number;
  showPercentage?: boolean;
  formatValue?: (value: number) => string;
}

export function HorizontalBarChart({
  data,
  maxValue: globalMax,
  showPercentage = true,
  formatValue = (v) => v.toString(),
}: HorizontalBarChartProps) {
  const computedMax = globalMax ?? Math.max(...data.map((d) => d.maxValue ?? d.value), 1);

  return (
    <div className="h-bar">
      {data.map((item, index) => {
        const itemMax = item.maxValue ?? computedMax;
        const percent = (item.value / itemMax) * 100;

        return (
          <div key={`${item.label}-${index}`} className="h-bar-item">
            <div className="h-bar-label">
              <span className="h-bar-label-text truncate">{item.label}</span>
              <span className="h-bar-label-value">
                {showPercentage ? `${percent.toFixed(0)}%` : formatValue(item.value)}
              </span>
            </div>
            <div className="h-bar-track">
              <div className="h-bar-fill" style={{ width: `${Math.min(100, percent)}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
