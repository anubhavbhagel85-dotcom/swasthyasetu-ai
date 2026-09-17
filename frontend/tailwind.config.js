/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAF7F0",
        ink: "#231F20",
        indigo: {
          DEFAULT: "#1E2A44",
          light: "#2E3D5E",
        },
        marigold: {
          DEFAULT: "#E8A33D",
          light: "#F4C878",
          dark: "#C97F20",
        },
        sage: {
          DEFAULT: "#4C7A5D",
          light: "#DCEADF",
        },
        amber: {
          DEFAULT: "#C97F2E",
          light: "#F6E4CB",
        },
        urgent: {
          DEFAULT: "#D1495B",
          light: "#FBE1E4",
        },
        emergency: {
          DEFAULT: "#A6291F",
          light: "#F8DAD6",
        },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Hind", "Manrope", "system-ui", "sans-serif"],
      },
      borderRadius: {
        chat: "18px",
      },
    },
  },
  plugins: [],
};
