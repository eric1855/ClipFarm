/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.{html,js}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          black: '#0a0a0a',
          dark: '#0d0d0d',
          panel: '#111111',
          green: '#00ff41',
          'green-dim': '#0a3d0a',
          'green-mid': '#00b330',
          amber: '#ffb000',
          cyan: '#00d4ff',
          red: '#ff0040',
          white: '#b0ffb0',
        },
      },
      fontFamily: {
        mono: ['"Fira Code"', '"JetBrains Mono"', 'Consolas', 'Monaco', '"Courier New"', 'monospace'],
      },
      animation: {
        'blink': 'blink 1s step-end infinite',
        'flicker': 'flicker 4s infinite',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
        'boot-1': 'fadeInLine 0.3s ease-out 0.2s both',
        'boot-2': 'fadeInLine 0.3s ease-out 0.5s both',
        'boot-3': 'fadeInLine 0.3s ease-out 0.8s both',
        'boot-4': 'fadeInLine 0.3s ease-out 1.1s both',
        'boot-5': 'fadeInLine 0.3s ease-out 1.4s both',
        'boot-6': 'fadeInLine 0.3s ease-out 1.7s both',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        flicker: {
          '0%, 100%': { opacity: '1' },
          '92%': { opacity: '1' },
          '93%': { opacity: '0.8' },
          '94%': { opacity: '1' },
          '96%': { opacity: '0.9' },
          '97%': { opacity: '1' },
        },
        glowPulse: {
          '0%, 100%': { textShadow: '0 0 5px currentColor' },
          '50%': { textShadow: '0 0 20px currentColor, 0 0 40px currentColor' },
        },
        fadeInLine: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
