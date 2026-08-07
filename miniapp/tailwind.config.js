/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{html,js,ts,jsx,tsx,vue}",
    "!./src/uni_modules/**/*",
    "!./node_modules/**/*",
    "!./dist/**/*",
    "!./unpackage/**/*",
  ],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        lime: {
          DEFAULT: "#C8DA2B",
          soft: "#F0F5CE",
          dark: "#A8B822",
        },
        olive: {
          DEFAULT: "#242B1F",
          mid: "#3A4433",
          light: "#6B7562",
        },
        paper: "#F2F2EF",
        ink: "#171B14",
      },
      borderRadius: {
        card: "20px",
        hero: "28px",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "PingFang SC",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  corePlugins: {
    // 小程序不需要 Tailwind 的 preflight 全局重置
    preflight: false,
  },
  plugins: [],
};
