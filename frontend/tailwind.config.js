/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0B0F14',
        surface: '#131922',
        raised: '#1B2330',
        border: '#2A3441',
        ink: '#E7ECF2',
        muted: '#8A96A6',
        faint: '#5B6675',
        signal: {
          DEFAULT: '#FF8A3D',
          dim: '#3D2A1B'
        },
        active: {
          DEFAULT: '#4FD1C5',
          dim: '#123B38'
        },
        danger: {
          DEFAULT: '#FF5D5D',
          dim: '#3A1A1A'
        }
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace']
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(79,209,197,0.25), 0 0 20px rgba(79,209,197,0.15)',
        signalGlow: '0 0 0 1px rgba(255,138,61,0.3), 0 0 20px rgba(255,138,61,0.18)'
      },
      keyframes: {
        pulseRing: {
          '0%': { boxShadow: '0 0 0 0 rgba(79,209,197,0.45)' },
          '70%': { boxShadow: '0 0 0 10px rgba(79,209,197,0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(79,209,197,0)' }
        },
        flow: {
          '0%': { backgroundPosition: '0% 0' },
          '100%': { backgroundPosition: '200% 0' }
        }
      },
      animation: {
        pulseRing: 'pulseRing 1.8s ease-out infinite',
        flow: 'flow 3s linear infinite'
      }
    }
  },
  plugins: []
}
