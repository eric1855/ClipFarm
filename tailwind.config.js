/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.{html,js}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        midnight: {
          950: '#050810',
          900: '#0a0e1a',
          800: '#0f1424',
          700: '#1a1f2e',
          600: '#242a3d',
          500: '#2e354c',
          400: '#3d4560',
          300: '#525b78',
          200: '#6b7494',
          100: '#8b93b0',
        },
        neon: {
          violet: '#7c3aed',
          'violet-light': '#a78bfa',
          cyan: '#06b6d4',
          'cyan-light': '#22d3ee',
          pink: '#ec4899',
          'pink-light': '#f472b6',
          green: '#10b981',
          amber: '#f59e0b',
          red: '#ef4444',
          blue: '#3b82f6',
        }
      },
      fontFamily: {
        inter: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'glow-pulse-fast': 'glow-pulse 1.5s ease-in-out infinite',
        'border-glow': 'border-glow 3s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'float-slow': 'float 8s ease-in-out infinite',
        'float-delayed': 'float 6s ease-in-out 2s infinite',
        'shimmer': 'shimmer 2s infinite',
        'scan': 'scan 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.6s ease-out forwards',
        'fade-in-up': 'fade-in-up 0.6s ease-out forwards',
        'slide-up': 'slide-up 0.5s ease-out forwards',
        'slide-down': 'slide-down 0.5s ease-out forwards',
        'scale-in': 'scale-in 0.3s ease-out forwards',
        'spin-slow': 'spin 3s linear infinite',
        'gradient-shift': 'gradient-shift 8s ease infinite',
        'particle-float': 'particle-float 3s ease-in-out infinite',
        'film-scroll': 'film-scroll 20s linear infinite',
        'pulse-ring': 'pulse-ring 2s ease-out infinite',
        'neon-flicker': 'neon-flicker 3s ease-in-out infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
        'border-glow': {
          '0%, 100%': { borderColor: 'rgba(124, 58, 237, 0.3)' },
          '50%': { borderColor: 'rgba(124, 58, 237, 0.6)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'scan': {
          '0%': { left: '-30%' },
          '100%': { left: '130%' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'particle-float': {
          '0%, 100%': { transform: 'translateY(0) translateX(0) scale(1)', opacity: '0.6' },
          '25%': { transform: 'translateY(-15px) translateX(5px) scale(1.1)', opacity: '1' },
          '50%': { transform: 'translateY(-5px) translateX(-5px) scale(0.9)', opacity: '0.8' },
          '75%': { transform: 'translateY(-20px) translateX(3px) scale(1.05)', opacity: '0.7' },
        },
        'film-scroll': {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '100%': { transform: 'scale(2.5)', opacity: '0' },
        },
        'neon-flicker': {
          '0%, 100%': { opacity: '1' },
          '41%': { opacity: '1' },
          '42%': { opacity: '0.8' },
          '43%': { opacity: '1' },
          '45%': { opacity: '0.3' },
          '46%': { opacity: '1' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'neon-violet': '0 0 20px rgba(124, 58, 237, 0.3), 0 0 60px rgba(124, 58, 237, 0.1)',
        'neon-cyan': '0 0 20px rgba(6, 182, 212, 0.3), 0 0 60px rgba(6, 182, 212, 0.1)',
        'neon-pink': '0 0 20px rgba(236, 72, 153, 0.3), 0 0 60px rgba(236, 72, 153, 0.1)',
        'neon-violet-lg': '0 0 30px rgba(124, 58, 237, 0.4), 0 0 80px rgba(124, 58, 237, 0.15)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3)',
        'glass-lg': '0 16px 48px rgba(0, 0, 0, 0.4)',
      },
    },
  },
  plugins: [],
}
