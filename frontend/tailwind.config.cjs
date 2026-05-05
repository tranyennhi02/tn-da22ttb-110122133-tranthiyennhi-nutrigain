module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        nutriblue: '#115E59',
        nutrigreen: '#0EA5A0',
        navy: '#0b2747',
        accent: '#FF9F43',
      },
      borderRadius: {
        'xl-lg': '1rem',
      },
    },
  },
  plugins: [],
};
