import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        ink: '#0b2438',
        muted: '#5d6b7a',
        canvas: '#f4f7fa',
        line: '#d8e1ea',
        brand: '#005da8',
        emerald: '#2f7d68',
        amber: '#b77816',
        rose: '#ef4444',
      },
      boxShadow: {
        panel: '0 14px 34px rgba(8, 31, 52, 0.08)',
        subtle: '0 8px 22px rgba(8, 31, 52, 0.06)',
      },
    },
  },
  plugins: [],
} satisfies Config;
