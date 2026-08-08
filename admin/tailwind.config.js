/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        olive: {
          50: '#f8f7f4',
          100: '#f0ede6',
          200: '#e2dccb',
          300: '#cfc5a8',
          400: '#bba985',
          500: '#a8906a',
          600: '#9b7e5e',
          700: '#81664e',
          800: '#6a5443',
          900: '#574639',
          950: '#2e241d',
        },
        lime: {
          50: '#f7fce4',
          100: '#ecf8c5',
          200: '#daf196',
          300: '#c0e55e',
          400: '#a8d634',
          500: '#8bbf16',
          600: '#6b9a0e',
          700: '#51740f',
          800: '#425c13',
          900: '#394e16',
          950: '#1d2b07',
        },
      },
    },
  },
  plugins: [],
}
