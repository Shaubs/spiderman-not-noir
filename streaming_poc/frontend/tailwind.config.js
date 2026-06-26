/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'spidey-red': '#CC0000',
        'spidey-blue': '#003366',
        'symbiote-dark': '#1a0a2e',
        'symbiote-purple': '#320050',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 5px #CC0000, 0 0 10px #CC0000' },
          '50%': { boxShadow: '0 0 20px #CC0000, 0 0 30px #CC0000' },
        },
      },
    },
  },
  plugins: [],
}
