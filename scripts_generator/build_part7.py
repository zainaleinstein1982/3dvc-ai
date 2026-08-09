import os

FILES = {
    "3dvc/frontend/package.json": """{
  "name": "3dvc-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "three": "^0.165.0",
    "@react-three/fiber": "^8.16.8",
    "@react-three/drei": "^9.108.4",
    "livekit-client": "^2.0.4",
    "@mediapipe/tasks-vision": "^0.10.14"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "@types/three": "^0.165",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3"
  }
}
""",
    "3dvc/frontend/next.config.mjs": """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
};
export default nextConfig;
""",
    "3dvc/frontend/tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
""",
    "3dvc/frontend/tailwind.config.ts": """import type { Config } from 'tailwindcss';
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { background: 'hsl(240 10% 4%)', foreground: 'hsl(0 0% 98%)' } } },
  plugins: [],
};
export default config;
""",
    "3dvc/frontend/postcss.config.js": """module.exports = {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
""",
    "3dvc/frontend/src/app/layout.tsx": """import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = {
  title: '3DVC AI',
  description: 'AI-Mediated 3D Video Conferencing',
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
""",
    "3dvc/frontend/src/app/page.tsx": """import dynamic from 'next/dynamic';
const Room = dynamic(() => import('@/components/Room'), { ssr: false });
export default function Page() { return <Room />; }
""",
    "3dvc/frontend/src/app/globals.css": """@tailwind base;
@tailwind components;
@tailwind utilities;
:root {
  --background: 240 10% 4%;
  --foreground: 0 0% 98%;
}
html, body { background: hsl(var(--background)); color: hsl(var(--foreground)); }
"""
}

def create_files():
    for filepath, content in FILES.items():
        full_path = os.path.join(os.getcwd(), filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Created: {filepath}")

if __name__ == "__main__":
    create_files()
