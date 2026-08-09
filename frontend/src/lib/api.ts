let accessToken: string | null = null;
export const setAccessToken = (token: string | null) => { accessToken = token; };

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://3dvc-ai-production.up.railway.app';
  
  // Pastikan URL tujuan mendukung absolute path jika diawali dengan /api
  const targetUrl = url.startsWith('http') ? url : `${API_URL}${url}`;

  const headers: Record<string, string> = { 
    ...(options.headers as Record<string, string>), 
    'Authorization': `Bearer ${accessToken}`, 
    'Content-Type': 'application/json' 
  };
  
  let res = await fetch(targetUrl, { ...options, headers });

  if (res.status === 401) {
    const refreshRes = await fetch(`${API_URL}/api/auth/refresh`, { 
      method: 'POST', 
      credentials: 'include' 
    });
    
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      setAccessToken(data.access_token);
      headers['Authorization'] = `Bearer ${data.access_token}`;
      res = await fetch(targetUrl, { ...options, headers });
    } else {
      window.location.reload();
      throw new Error('Session expired');
    }
  }
  return res;
}