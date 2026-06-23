module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        nutriblue: '#115E59', // legacy
        nutrigreen: '#0EA5A0', // legacy
        accent: '#FF9F43', // legacy
        
        // New Brand Colors
        'brand-navy': '#0B2A4A',
        'brand-mint': '#ECFDF5',
        'brand-primary': '#10B981',
        'brand-primary-dark': '#047857',
        'brand-orange': '#FB923C',
        'brand-orange-dark': '#F97316',
        'brand-cream': '#FFF7ED',
        'brand-text-main': '#0F172A',
        'brand-text-sub': '#64748B',
        'brand-border': '#E2E8F0',
        'brand-surface': '#FFFFFF',
        'brand-soft': '#F8FAFC',
        
        // System Colors
        'sys-danger': '#EF4444',
        'sys-info': '#3B82F6',
        'sys-warning': '#F59E0B',
      },
      borderRadius: {
        'xl-lg': '1rem',
      },
    },
  },
  plugins: [],
};
