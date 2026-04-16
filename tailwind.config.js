export default {
  darkMode: 'class', // better than data-theme
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1877f2',
        'primary-soft': '#e7f3ff',

        bg: '#f0f2f5',
        'bg-dark': '#121212',

        card: '#ffffff',
        'card-dark': '#272727',

        border: '#dcdfe3',
        'border-dark': '#1f2020',

        text: '#050505',
        'text-dark': '#e1e8ed',

        muted: '#65676b',
        'muted-dark': '#8899a6',

        hover: '#f0f2f5',
        'hover-dark': '#222',

        success: '#22c55e',
        danger: '#ef4444',
      },

      boxShadow: {
        soft: '0 2px 10px rgba(0,0,0,0.05)',
        card: '0 4px 20px rgba(0,0,0,0.08)',
      },

      borderRadius: {
        xl: '12px',
        '2xl': '16px',
      }
    }
  },
  plugins: [],
}