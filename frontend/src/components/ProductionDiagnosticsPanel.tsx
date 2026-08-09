'use client';
import { useState, useEffect } from 'react';

export default function ProductionDiagnosticsPanel({ token }: { token?: string }) {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const API_URL = 'https://3dvc-ai-production.up.railway.app';
        const headers: HeadersInit = {};
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const res = await fetch(`${API_URL}/api/health/admin-diagnostics`, { headers });
        if (res.ok) {
          setHealth(await res.json());
        } else {
          setHealth({ status: 'online_restricted' });
        }
      } catch (e) {
        setHealth({ status: 'backend_offline' });
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [token]);

  return (
    <div className="absolute top-4 right-4 bg-black/90 p-4 rounded-xl border border-white/10 w-80 text-xs font-mono z-50">
      <div className="text-sm font-bold mb-2 text-emerald-400">SYSTEM HEALTH</div>
      {health ? (
        <div className="space-y-1">
          <div>Status: <span className="text-emerald-400">{health.status}</span></div>
          {health.dependencies && (
            <>
              <div>Redis: <span className="text-emerald-400">{health.dependencies.redis}</span></div>
              <div>MinIO: <span className="text-emerald-400">{health.dependencies.minio}</span></div>
              <div>GPU Workers: <span className="text-cyan-400">{health.dependencies.gpu_workers}</span></div>
            </>
          )}
        </div>
      ) : <div className="text-white/50">Checking...</div>}
    </div>
  );
}