/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.{html,js}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#fafafa',
          card: '#ffffff',
        },
        ink: {
          DEFAULT: '#0a0a0a',
          secondary: '#6b7280',
          tertiary: '#9ca3af',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        'tile': '16px',
      },
      boxShadow: {
        'tile': '0 1px 3px rgba(0,0,0,0.08)',
        'tile-hover': '0 8px 25px rgba(0,0,0,0.12)',
        'btn': '0 2px 8px rgba(0,0,0,0.15)',
        'btn-hover': '0 4px 16px rgba(0,0,0,0.2)',
      },
      animation: {
        'tile-in': 'tileIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both',
        'fade-in': 'fadeIn 0.4s ease-out both',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both',
        'hue-shift': 'hueShift 30s linear infinite',
        'border-sweep': 'borderSweep 3s linear infinite',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'spin': 'spin 1s linear infinite',
        'success-bounce': 'successBounce 0.4s ease both',
      },
      keyframes: {
        tileIn: {
          '0%': { opacity: '0', transform: 'scale(0.95) translateY(8px)' },
          '100%': { opacity: '1', transform: 'scale(1) translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        hueShift: {
          '0%': { filter: 'hue-rotate(0deg)' },
          '100%': { filter: 'hue-rotate(360deg)' },
        },
        borderSweep: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        successBounce: {
          '0%': { transform: 'scale(1)' },
          '30%': { transform: 'scale(0.97)' },
          '60%': { transform: 'scale(1.02)' },
          '100%': { transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
