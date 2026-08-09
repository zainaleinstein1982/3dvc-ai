import './globals.css';
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
