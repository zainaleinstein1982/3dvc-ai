import type { Config } from 'tailwindcss';
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { background: 'hsl(240 10% 4%)', foreground: 'hsl(0 0% 98%)' } } },
  plugins: [],
};
export default config;
