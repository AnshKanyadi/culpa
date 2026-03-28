import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Culpa brand palette — dark & premium
        culpa: {
          bg: '#0a0a0b',
          surface: '#111113',
          border: '#1e1e21',
          muted: '#2a2a2e',
          text: '#e8e8ea',
          'text-dim': '#8888a0',
          blue: '#4f8ef7',
          'blue-dim': '#1d3461',
          purple: '#9b5de5',
          'purple-dim': '#2d1b4e',
          green: '#2dd4a0',
          'green-dim': '#0d3327',
          orange: '#f7a84f',
          'orange-dim': '#3d2808',
          red: '#f75f5f',
          'red-dim': '#3d0f0f',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-slow': 'pulse 3s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

export default config
