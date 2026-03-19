/** @type {import('tailwindcss').Config} */
module.exports = {
  // Tightened content list: include only files that contain Tailwind classes
  content: [
    './index.html',
    './generator/**/*.html',
    './generator/**/**/*.html',
    './rmk-theme/**/*.php',
    './rmk-theme/**/**/*.php'
  ],
  theme: {
    extend: {
      colors: {
        'scout-brown': '#654B38',
        'scout-taupe': '#6B5B51',
        'scout-gray': '#9E9A9A',
        'scout-cream': '#DEDCDA',
        'scout-white': '#F5F5F5',
        'scout-green': '#2D5016',
        'scout-footer-link': '#FFE8B0'
      }
    }
  },
  plugins: []
}
