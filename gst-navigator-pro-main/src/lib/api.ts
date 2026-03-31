import type { AppSettings } from '@/types/client';

function getSettings(): AppSettings {
  const stored = localStorage.getItem('gst_settings');
  if (stored) return JSON.parse(stored);
  return {
    dbProxyUrl: 'http://localhost:9000',
    dbProxyUser: 'admin',
    dbProxyPass: 'password',
    serviceApiUrl: 'http://localhost:8000',
  };
}

// --- Service API calls ---

export async function serviceGet(path: string, token?: string | null): Promise<any> {
  const settings = getSettings();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${settings.serviceApiUrl}${path}`, { headers });
  if (res.status === 401) throw new Error('SESSION_EXPIRED');
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function servicePost(path: string, body: any, token?: string | null): Promise<any> {
  const settings = getSettings();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${settings.serviceApiUrl}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (res.status === 401) throw new Error('SESSION_EXPIRED');
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

// --- DB Proxy calls ---

export async function dbProxyFetch(gstin?: string | string[], tables?: string[]): Promise<Record<string, any[]>> {
  const settings = getSettings();
  const params = new URLSearchParams();
  if (gstin) {
    const gstins = Array.isArray(gstin) ? gstin : [gstin];
    gstins.forEach(g => params.append('gstin', g));
  }
  if (tables) {
    tables.forEach(t => params.append('tables', t));
  }
  const creds = btoa(`${settings.dbProxyUser}:${settings.dbProxyPass}`);
  const res = await fetch(`${settings.dbProxyUrl}/fetch?${params.toString()}`, {
    headers: { 'Authorization': `Basic ${creds}` },
  });
  if (!res.ok) throw new Error(`DB Proxy error: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function fetchAvailablePeriods(gstin?: string): Promise<{ periods: Array<{ year: string; month: string }> }> {
  const settings = getSettings();
  const params = new URLSearchParams();
  if (gstin) {
    params.append('gstin', gstin);
  }
  const creds = btoa(`${settings.dbProxyUser}:${settings.dbProxyPass}`);
  const res = await fetch(`${settings.dbProxyUrl}/available-periods?${params.toString()}`, {
    headers: { 'Authorization': `Basic ${creds}` },
  });
  if (!res.ok) throw new Error(`DB Proxy error: ${res.status} ${res.statusText}`);
  return res.json();
}

// --- Auth ---

export async function generateOTP(username: string, gstin: string): Promise<any> {
  return servicePost('/auth/generate-otp', { username, gstin });
}

export async function verifyOTP(username: string, gstin: string, otp: string): Promise<any> {
  return servicePost('/auth/verify-otp', { username, gstin, otp });
}

export async function refreshSession(gstin: string): Promise<any> {
  return servicePost('/auth/refresh', { gstin });
}

export async function getSessionStatus(gstin: string): Promise<any> {
  return serviceGet(`/auth/session/${gstin}`);
}

// --- Test connections ---

export async function testServiceApi(): Promise<boolean> {
  try {
    const settings = getSettings();
    const res = await fetch(`${settings.serviceApiUrl}/docs`, { method: 'HEAD' });
    return res.ok || res.status === 405 || res.status === 200;
  } catch {
    return false;
  }
}

export async function testDbProxy(): Promise<boolean> {
  try {
    const settings = getSettings();
    const creds = btoa(`${settings.dbProxyUser}:${settings.dbProxyPass}`);
    const res = await fetch(`${settings.dbProxyUrl}/fetch`, {
      headers: { 'Authorization': `Basic ${creds}` },
    });
    return res.ok;
  } catch {
    return false;
  }
}
