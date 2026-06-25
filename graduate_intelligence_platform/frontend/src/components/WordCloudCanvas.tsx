import { useEffect, useRef, useState } from 'react';
import WordCloud from 'wordcloud';

export interface CloudWord {
  text: string;
  weight: number;
  color: string;
  bold: boolean;
  tooltip?: string;
}

interface Props {
  words: CloudWord[];
  height?: number;
  scheme: 'navy' | 'red';
}

// Color tiers based on normalized weight (0–1)
function tierColor(norm: number, scheme: 'navy' | 'red'): string {
  if (scheme === 'navy') {
    if (norm >= 0.75) return '#0D2158';
    if (norm >= 0.50) return '#2563EB';
    if (norm >= 0.30) return '#5B83D1';
    return '#93A5C9';
  } else {
    if (norm >= 0.75) return '#7F1D1D';
    if (norm >= 0.50) return '#B91C1C';
    if (norm >= 0.30) return '#DC2626';
    return '#F87171';
  }
}

export default function WordCloudCanvas({ words, height = 340, scheme }: Props) {
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const wrapRef    = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap   = wrapRef.current;
    if (!canvas || !wrap || words.length === 0) return;

    // Size canvas to container
    const W = wrap.clientWidth || 700;
    canvas.width  = W;
    canvas.height = height;

    const maxW = Math.max(...words.map(w => w.weight), 1);

    WordCloud(canvas, {
      list:            words.map(w => [w.text, w.weight] as [string, number]),
      shape:           'circle',
      backgroundColor: 'transparent',
      gridSize:        Math.round(W / 60),
      weightFactor:    (size: number) => Math.pow(size / maxW, 0.45) * (W / 14),
      color:           (_word: string, weight: string | number) => {
        const norm = (weight as number) / maxW;
        return tierColor(norm, scheme);
      },
      fontFamily:      'system-ui, -apple-system, sans-serif',
      fontWeight:      ((_word: string, weight: string | number) => {
        const norm = (weight as number) / maxW;
        return norm >= 0.5 ? '800' : norm >= 0.3 ? '700' : '500';
      }) as unknown as string,
      rotateRatio:     0.3,
      minRotation:     -Math.PI / 12,   // -15°
      maxRotation:      Math.PI / 12,   //  15°
      minSize:         10,
      drawOutOfBound:  false,
      shrinkToFit:     true,

      hover: ((item: WordCloud.ListEntry | null, _dim: unknown, event: MouseEvent) => {
        if (!item || !wrap) { setTooltip(null); return; }
        const word = words.find(w => w.text === item[0]);
        if (!word?.tooltip) { setTooltip(null); return; }
        const rect = wrap.getBoundingClientRect();
        setTooltip({
          text: word.tooltip,
          x: event.clientX - rect.left + 12,
          y: event.clientY - rect.top  - 8,
        });
      }) as WordCloud.Options['hover'],

      click: ((item: WordCloud.ListEntry | null) => {
        if (!item) return;
        const word = words.find(w => w.text === item[0]);
        if (word?.tooltip) alert(word.tooltip);
      }) as WordCloud.Options['click'],
    });

    // Cleanup on unmount / re-render
    return () => { WordCloud.stop?.(); };
  }, [words, height, scheme]);

  // Debounced resize
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const onResize = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const canvas = canvasRef.current;
        const wrap   = wrapRef.current;
        if (!canvas || !wrap || words.length === 0) return;
        const W = wrap.clientWidth || 700;
        canvas.width  = W;
        canvas.height = height;
        // re-trigger the wordcloud effect by dispatching a synthetic resize
        // (simplest: just re-run by changing a key — parent handles via key prop)
      }, 250);
    };
    window.addEventListener('resize', onResize);
    return () => { clearTimeout(timer); window.removeEventListener('resize', onResize); };
  }, [words, height, scheme]);

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}
      onMouseLeave={() => setTooltip(null)}>
      <canvas ref={canvasRef} style={{ display: 'block', width: '100%', height }} />
      {tooltip && (
        <div style={{
          position: 'absolute',
          left: tooltip.x,
          top:  tooltip.y,
          background: '#1E293B',
          color: '#F8FAFC',
          fontSize: 11,
          fontWeight: 500,
          lineHeight: 1.5,
          padding: '6px 10px',
          borderRadius: 6,
          pointerEvents: 'none',
          maxWidth: 280,
          boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
          zIndex: 100,
          whiteSpace: 'pre-wrap',
        }}>
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
