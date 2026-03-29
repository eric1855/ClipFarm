/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.{html,js}",
    "./public/index.html"
  ],
  theme: {
    borderRadius: {
      'none': '0',
      DEFAULT: '0',
      'full': '0',
      'lg': '0',
      'md': '0',
      'sm': '0',
      'xl': '0',
      '2xl': '0',
      '3xl': '0',
    },
    extend: {
      colors: {
        arcade: {
          bg: '#0a0a1a',
          dark: '#1a1a2e',
          panel: '#16213e',
          green: '#00ff00',
          cyan: '#00ffff',
          pink: '#ff00ff',
          yellow: '#ffff00',
          red: '#ff0000',
          orange: '#ff8800',
          blue: '#4444ff',
          purple: '#aa44ff',
          white: '#ffffff',
          dim: '#888899',
        },
      },
      fontFamily: {
        'pixel': ['"Press Start 2P"', 'monospace'],
      },
      boxShadow: {
        'pixel': '0 -4px 0 0 #fff, 0 4px 0 0 #fff, -4px 0 0 0 #fff, 4px 0 0 0 #fff',
        'pixel-green': '0 -4px 0 0 #00ff00, 0 4px 0 0 #00ff00, -4px 0 0 0 #00ff00, 4px 0 0 0 #00ff00',
        'pixel-cyan': '0 -4px 0 0 #00ffff, 0 4px 0 0 #00ffff, -4px 0 0 0 #00ffff, 4px 0 0 0 #00ffff',
        'pixel-pink': '0 -4px 0 0 #ff00ff, 0 4px 0 0 #ff00ff, -4px 0 0 0 #ff00ff, 4px 0 0 0 #ff00ff',
        'pixel-yellow': '0 -4px 0 0 #ffff00, 0 4px 0 0 #ffff00, -4px 0 0 0 #ffff00, 4px 0 0 0 #ffff00',
        'pixel-red': '0 -4px 0 0 #ff0000, 0 4px 0 0 #ff0000, -4px 0 0 0 #ff0000, 4px 0 0 0 #ff0000',
        'pixel-orange': '0 -4px 0 0 #ff8800, 0 4px 0 0 #ff8800, -4px 0 0 0 #ff8800, 4px 0 0 0 #ff8800',
        'screen-glow': '0 0 80px rgba(0,255,0,0.08), 0 0 160px rgba(0,255,0,0.04)',
        'screen-glow-cyan': '0 0 80px rgba(0,255,255,0.08), 0 0 160px rgba(0,255,255,0.04)',
      },
      borderWidth: {
        '3': '3px',
        '4': '4px',
      },
      animation: {
        'blink': 'blink 1s steps(1) infinite',
        'blink-slow': 'blink 2s steps(1) infinite',
        'float': 'float 2s ease-in-out infinite',
        'pixel-pop': 'pixelPop 0.4s steps(4) both',
        'crt-flicker': 'crtFlicker 4s linear infinite',
        'twinkle': 'twinkle 3s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 1.5s ease-in-out infinite',
        'marquee': 'marquee 20s linear infinite',
        'note-float': 'noteFloat 1s ease-out forwards',
        'runner': 'runAcross 3s linear infinite',
      },
      keyframes: {
        blink: {
          '0%, 49%': { opacity: '1' },
          '50%, 100%': { opacity: '0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        pixelPop: {
          '0%': { transform: 'scale(0)', opacity: '0' },
          '33%': { transform: 'scale(0.5)' },
          '66%': { transform: 'scale(1.1)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        crtFlicker: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.97' },
          '75%': { opacity: '0.99' },
        },
        twinkle: {
          '0%, 100%': { opacity: '0.2' },
          '50%': { opacity: '1' },
        },
        noteFloat: {
          '0%': { transform: 'translateY(0) scale(1)', opacity: '1' },
          '100%': { transform: 'translateY(-30px) scale(0.5)', opacity: '0' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 8px rgba(0,255,255,0.4), 0 0 16px rgba(0,255,255,0.2)' },
          '50%': { boxShadow: '0 0 16px rgba(0,255,255,0.8), 0 0 32px rgba(0,255,255,0.4)' },
        },
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        runAcross: {
          '0%': { left: '-16px' },
          '100%': { left: '100%' },
        },
      },
    },
  },
  plugins: [],
}
