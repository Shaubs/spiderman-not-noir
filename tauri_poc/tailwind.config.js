/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'spidey-red': '#B71C1C',
        'spidey-blue': '#1565C0',
        'symbiote-purple': '#4B0082',
      },
    },
  },
  plugins: [],
}
