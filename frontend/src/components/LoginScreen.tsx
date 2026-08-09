'use client';
import { useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://3dvc-ai-production.up.railway.app';

export default function LoginScreen({ onLogin }: { onLogin: (token: string, user: any) => void }) {
  const [email, setEmail] = useState('admin@3dvc.ai');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        onLogin(data.access_token, data.user);
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('Tidak bisa terhubung ke server. Cek koneksi atau coba lagi.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-black text-white gap-4">
      <h1 className="text-2xl font-bold">3DVC AI Sign In</h1>
      <input id="email" name="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="bg-white/10 px-4 py-2 rounded-md" />
      <input id="password" name="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="bg-white/10 px-4 py-2 rounded-md" />
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <button onClick={handleLogin} disabled={loading} className="bg-emerald-500 text-black px-6 py-2 rounded-md font-bold disabled:opacity-50">
        {loading ? 'Signing in...' : 'Sign In'}
      </button>
    </div>
  );
}