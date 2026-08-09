'use client';
import { useState } from 'react';

export default function LoginScreen({ onLogin }: { onLogin: (token: string, user: any) => void }) {
  const [email, setEmail] = useState('admin@3dvc.ai');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');

  const handleLogin = async () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://3dvc-ai-production.up.railway.app';
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (data.access_token) onLogin(data.access_token, data.user);
    else setError(data.detail || 'Login failed');
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-black text-white gap-4">
      <h1 className="text-2xl font-bold">3DVC AI Sign In</h1>
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="bg-white/10 px-4 py-2 rounded-md" />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="bg-white/10 px-4 py-2 rounded-md" />
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <button onClick={handleLogin} className="bg-emerald-500 text-black px-6 py-2 rounded-md font-bold">Sign In</button>
    </div>
  );
}