let accessToken: string | null = null;
export const setAccessToken = (token: string | null) => { accessToken = token; };

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers = { ...options.headers, 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' };
  let res = await fetch(url, { ...options, headers, credentials: 'include' });

  if (res.status === 401) {
    const refreshRes = await fetch('http://localhost:8000/api/auth/refresh', { method: 'POST', credentials: 'include' });
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      setAccessToken(data.access_token);
      headers['Authorization'] = `Bearer ${data.access_token}`;
      res = await fetch(url, { ...options, headers, credentials: 'include' });
    } else {
      window.location.reload();
      throw new Error('Session expired');
    }
  }
  return res;
}
