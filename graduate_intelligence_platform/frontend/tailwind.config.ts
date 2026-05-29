import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        // Institutional UNIR palette
        'unir-blue': '#003A70',
        'unir-blue-dark': '#002952',
        'unir-blue-light': '#0052A0',
        // Executive neutrals
        canvas: '#F8FAFC',
        'canvas-alt': '#F1F5F9',
        ink: '#1E293B',
        'ink-light': '#334155',
        muted: '#64748B',
        'muted-light': '#94A3B8',
        line: '#E2E8F0',
        'line-light': '#F1F5F9',
        // Status colors
        success: '#047857',
        'success-light': '#ECFDF5',
        warning: '#B45309',
        'warning-light': '#FFFBEB',
        danger: '#DC2626',
        'danger-light': '#FEF2F2',
        // Accent
        accent: '#003A70',
        'accent-light': '#EFF6FF',
      },
      boxShadow: {
        card: '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
        'card-hover': '0 4px 12px rgba(15, 23, 42, 0.08)',
        panel: '0 4px 16px rgba(15, 23, 42, 0.06)',
      },
      borderRadius: {
        DEFAULT: '6px',
      },
    },
  },
  plugins: [],
} satisfies Config;
