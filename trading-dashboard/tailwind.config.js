/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: { DEFAULT: '#1a1b23', light: '#22232d', lighter: '#2a2b37' },
        accent: { DEFAULT: '#6366f1', light: '#818cf8' },
        gain: '#10b981',
        loss: '#ef4444',
        muted: '#64748b',
      },
    },
  },
  plugins: [],
}
