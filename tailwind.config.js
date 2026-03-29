/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./public/**/*.{html,js}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        barn: {
          DEFAULT: '#b91c1c',
          dark: '#991b1b',
          light: '#dc2626',
        },
        sunflower: {
          DEFAULT: '#facc15',
          light: '#fde047',
          dark: '#eab308',
        },
        earth: {
          DEFAULT: '#78350f',
          light: '#92400e',
          dark: '#451a03',
        },
        forest: {
          DEFAULT: '#166534',
          light: '#15803d',
          dark: '#14532d',
        },
        cream: {
          DEFAULT: '#fefce8',
          50: '#fefce8',
          100: '#fef9c3',
          200: '#fef08a',
        },
        sky: {
          light: '#bae6fd',
          DEFAULT: '#7dd3fc',
          dark: '#38bdf8',
        },
        jet: '#0f0f0f',
        wood: {
          DEFAULT: '#a0522d',
          light: '#cd853f',
          dark: '#8b4513',
        },
      },
      boxShadow: {
        'brutal': '6px 6px 0px #0f0f0f',
        'brutal-sm': '4px 4px 0px #0f0f0f',
        'brutal-lg': '8px 8px 0px #0f0f0f',
        'brutal-hover': '3px 3px 0px #0f0f0f',
        'brutal-active': '0px 0px 0px #0f0f0f',
        'barn': '6px 6px 0px #b91c1c',
        'wood': '6px 6px 0px #78350f',
        'forest': '6px 6px 0px #166534',
      },
      borderWidth: {
        '3': '3px',
        '4': '4px',
        '5': '5px',
      },
      fontFamily: {
        'farm': ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'marquee': 'marquee 25s linear infinite',
        'bob': 'bob 2s ease-in-out infinite',
        'float-seed': 'floatSeed 6s ease-in-out infinite',
        'grow-crop': 'growCrop 3s ease-out forwards',
        'sun-rise': 'sunRise 3s ease-out forwards',
        'tractor': 'tractorDrive 2s ease-in-out',
        'wiggle': 'wiggle 2.5s ease-in-out infinite',
        'bounce-sign': 'bounceSign 0.4s ease',
        'step-enter': 'stepEnter 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'step-exit': 'stepExit 0.3s ease-in forwards',
        'sprout': 'sprout 2s ease-out infinite',
        'slide-up': 'slideUp 0.5s ease-out both',
        'fade-in': 'fadeIn 0.4s ease-out both',
        'pop': 'pop 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) both',
      },
      keyframes: {
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        bob: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        floatSeed: {
          '0%': { transform: 'translateY(0) rotate(0deg)', opacity: '0' },
          '10%': { opacity: '1' },
          '90%': { opacity: '1' },
          '100%': { transform: 'translateY(-80px) rotate(360deg)', opacity: '0' },
        },
        growCrop: {
          '0%': { transform: 'scaleY(0)', transformOrigin: 'bottom' },
          '100%': { transform: 'scaleY(1)', transformOrigin: 'bottom' },
        },
        sunRise: {
          '0%': { transform: 'translateY(40px)', opacity: '0.3' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        tractorDrive: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(400%)' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-2deg)' },
          '50%': { transform: 'rotate(2deg)' },
        },
        bounceSign: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
          '100%': { transform: 'scale(1)' },
        },
        stepEnter: {
          '0%': { transform: 'translateX(60px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        stepExit: {
          '0%': { transform: 'translateX(0)', opacity: '1' },
          '100%': { transform: 'translateX(-60px)', opacity: '0' },
        },
        sprout: {
          '0%, 100%': { transform: 'scaleY(1)' },
          '50%': { transform: 'scaleY(1.1)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(30px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pop: {
          '0%': { transform: 'scale(0.8)', opacity: '0' },
          '80%': { transform: 'scale(1.1)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
