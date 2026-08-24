import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Light-theme surfaces — cool slate neutrals (harmonize with blue brand + semantic colors)
        surface: {
          canvas: '#dce4ed',
          DEFAULT: '#e9eef4',
          elevated: '#f5f8fb',
        },
        // Primary accent
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      keyframes: {
        'bell-shake': {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '20%': { transform: 'rotate(-14deg)' },
          '40%': { transform: 'rotate(14deg)' },
          '60%': { transform: 'rotate(-10deg)' },
          '80%': { transform: 'rotate(10deg)' },
        },
      },
      animation: {
        'bell-shake': 'bell-shake 0.6s ease-in-out',
      },
    },
  },
  plugins: [],
} satisfies Config
