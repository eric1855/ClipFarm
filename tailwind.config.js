/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.{html,js}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        crystal: {
          50: '#f0f4ff',
          100: '#dbe4ff',
          200: '#bac8ff',
          300: '#91a7ff',
          400: '#748ffc',
          500: '#5c7cfa',
          600: '#4c6ef5',
          700: '#4263eb',
          800: '#3b5bdb',
          900: '#364fc7',
        },
        prism: {
          blue: '#3b82f6',
          purple: '#8b5cf6',
          pink: '#ec4899',
          teal: '#14b8a6',
          cyan: '#06b6d4',
          indigo: '#6366f1',
        },
        surface: {
          base: '#f8fafc',
        }
      },
      fontFamily: {
        inter: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-delayed': 'float 6s ease-in-out 2s infinite',
        'float-slow': 'float 8s ease-in-out infinite',
        'shimmer': 'shimmer 3s ease-in-out infinite',
        'shimmer-fast': 'shimmer 1.5s ease-in-out infinite',
        'spin-slow': 'spin 20s linear infinite',
        'spin-reverse': 'spin-reverse 25s linear infinite',
        'pulse-prism': 'pulse-prism 4s ease-in-out infinite',
        'mesh-shift': 'mesh-shift 15s ease infinite',
        'entrance-up': 'entrance-up 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'entrance-scale': 'entrance-scale 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'rotate-wireframe': 'rotate-wireframe 30s linear infinite',
        'glow-pulse': 'glow-pulse 3s ease-in-out infinite',
        'holographic': 'holographic 6s ease infinite',
        'shine-sweep': 'shine-sweep 3s ease-in-out infinite',
        'card-float-1': 'card-float-1 7s ease-in-out infinite',
        'card-float-2': 'card-float-2 8s ease-in-out 1s infinite',
        'card-float-3': 'card-float-3 6s ease-in-out 0.5s infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'spin-reverse': {
          '0%': { transform: 'rotate(360deg)' },
          '100%': { transform: 'rotate(0deg)' },
        },
        'pulse-prism': {
          '0%, 100%': { opacity: '0.6', filter: 'hue-rotate(0deg)' },
          '50%': { opacity: '1', filter: 'hue-rotate(60deg)' },
        },
        'mesh-shift': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        'entrance-up': {
          '0%': { opacity: '0', transform: 'translateY(40px) scale(0.95)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'entrance-scale': {
          '0%': { opacity: '0', transform: 'scale(0.8)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'rotate-wireframe': {
          '0%': { transform: 'rotateX(0deg) rotateY(0deg) rotateZ(0deg)' },
          '100%': { transform: 'rotateX(360deg) rotateY(360deg) rotateZ(360deg)' },
        },
        'glow-pulse': {
          '0%, 100%': {
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.15), 0 0 60px rgba(99, 102, 241, 0.05)',
          },
          '50%': {
            boxShadow: '0 0 30px rgba(99, 102, 241, 0.3), 0 0 80px rgba(99, 102, 241, 0.1)',
          },
        },
        'holographic': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        'shine-sweep': {
          '0%': { left: '-100%' },
          '50%, 100%': { left: '200%' },
        },
        'card-float-1': {
          '0%, 100%': { transform: 'translateY(0px) rotateX(2deg) rotateY(-1deg)' },
          '50%': { transform: 'translateY(-8px) rotateX(0deg) rotateY(0deg)' },
        },
        'card-float-2': {
          '0%, 100%': { transform: 'translateY(0px) rotateX(1deg) rotateY(1deg)' },
          '50%': { transform: 'translateY(-10px) rotateX(-1deg) rotateY(-1deg)' },
        },
        'card-float-3': {
          '0%, 100%': { transform: 'translateY(0px) rotateX(-1deg) rotateY(2deg)' },
          '50%': { transform: 'translateY(-6px) rotateX(1deg) rotateY(0deg)' },
        },
      },
      backgroundSize: {
        '300%': '300% 300%',
        '400%': '400% 400%',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'crystal': '0 8px 32px rgba(99, 102, 241, 0.12), 0 2px 8px rgba(99, 102, 241, 0.08)',
        'crystal-lg': '0 16px 48px rgba(99, 102, 241, 0.15), 0 4px 16px rgba(99, 102, 241, 0.1)',
        'crystal-xl': '0 24px 64px rgba(99, 102, 241, 0.2), 0 8px 24px rgba(99, 102, 241, 0.12)',
        'prism': '0 8px 32px rgba(139, 92, 246, 0.15), 0 2px 8px rgba(59, 130, 246, 0.1)',
        'prism-lg': '0 16px 48px rgba(139, 92, 246, 0.2), 0 4px 16px rgba(59, 130, 246, 0.15)',
        'depth-1': '0 1px 2px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.04)',
        'depth-2': '0 2px 4px rgba(0,0,0,0.04), 0 4px 8px rgba(0,0,0,0.06), 0 8px 16px rgba(0,0,0,0.04)',
        'depth-3': '0 4px 8px rgba(0,0,0,0.04), 0 8px 16px rgba(0,0,0,0.06), 0 16px 32px rgba(0,0,0,0.06), 0 32px 64px rgba(0,0,0,0.04)',
        'inner-glow': 'inset 0 1px 0 rgba(255,255,255,0.8), inset 0 -1px 0 rgba(0,0,0,0.04)',
        '3d-button': '0 6px 0 rgba(67, 56, 202, 0.4), 0 8px 20px rgba(99, 102, 241, 0.25), inset 0 1px 0 rgba(255,255,255,0.3)',
        '3d-button-pressed': '0 2px 0 rgba(67, 56, 202, 0.4), 0 3px 6px rgba(99, 102, 241, 0.15), inset 0 1px 0 rgba(255,255,255,0.2)',
      },
    },
  },
  plugins: [],
}
