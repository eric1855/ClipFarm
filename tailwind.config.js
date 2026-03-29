/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.{html,js}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        cream: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
        },
        jet: '#0f0f0f',
        coral: {
          DEFAULT: '#ff6b6b',
          light: '#ff9a9a',
          dark: '#e85555',
        },
        electric: {
          yellow: '#facc15',
          blue: '#3b82f6',
          lime: '#84cc16',
          purple: '#a855f7',
        },
      },
      boxShadow: {
        'brutal': '8px 8px 0px #0f0f0f',
        'brutal-sm': '4px 4px 0px #0f0f0f',
        'brutal-lg': '12px 12px 0px #0f0f0f',
        'brutal-hover': '4px 4px 0px #0f0f0f',
        'brutal-active': '0px 0px 0px #0f0f0f',
        'brutal-yellow': '8px 8px 0px #facc15',
        'brutal-coral': '8px 8px 0px #ff6b6b',
        'brutal-blue': '8px 8px 0px #3b82f6',
        'brutal-lime': '8px 8px 0px #84cc16',
        'brutal-purple': '8px 8px 0px #a855f7',
        'brutal-inverse': '-4px -4px 0px #0f0f0f',
      },
      borderWidth: {
        '3': '3px',
        '4': '4px',
      },
      fontFamily: {
        'brutal': ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'wobble': 'wobble 0.5s ease-in-out',
        'bounce-in': 'bounceIn 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'sticker-peel': 'stickerPeel 0.3s ease-out',
        'marquee': 'marquee 20s linear infinite',
        'spin-slow': 'spin 3s linear infinite',
        'wiggle': 'wiggle 2.5s ease-in-out infinite',
        'pop': 'pop 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      },
      keyframes: {
        wobble: {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '25%': { transform: 'rotate(-2deg)' },
          '75%': { transform: 'rotate(2deg)' },
        },
        bounceIn: {
          '0%': { transform: 'scale(0.3)', opacity: '0' },
          '50%': { transform: 'scale(1.05)' },
          '70%': { transform: 'scale(0.9)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(30px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        stickerPeel: {
          '0%': { transform: 'perspective(800px) rotateY(0deg)' },
          '100%': { transform: 'perspective(800px) rotateY(-10deg)' },
        },
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-1deg)' },
          '50%': { transform: 'rotate(1deg)' },
        },
        pop: {
          '0%': { transform: 'scale(0.8)', opacity: '0' },
          '80%': { transform: 'scale(1.1)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      rotate: {
        '-2': '-2deg',
        '-1': '-1deg',
        '1': '1deg',
        '2': '2deg',
        '3': '3deg',
      },
    },
  },
  plugins: [],
}
