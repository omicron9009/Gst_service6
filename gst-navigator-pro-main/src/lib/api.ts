import type { AppSettings, ProxyClient } from '@/types/client';

const host = window.location.hostname;

function getSettings(): AppSettings {
  const stored = localStorage.getItem('gst_settings');
  if (stored) {
    const parsed = JSON.parse(stored);
    return {
      ...parsed,
      dbProxyUrl: `http://${host}:8050`,
      serviceApiUrl: `http://${host}:8000`,
    };
  }
  return {
    dbProxyUrl: `http://${host}:8050`,
    dbProxyUser: 'admin',
    dbProxyPass: 'root',
    serviceApiUrl: `http://${host}:8000`,
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

export async function servicePostFormData(path: string, formData: FormData, token?: string | null): Promise<any> {
  const settings = getSettings();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${settings.serviceApiUrl}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (res.status === 401) throw new Error('SESSION_EXPIRED');
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

// --- DB Proxy calls ---

export async function dbProxyFetch(gstin?: string | string[], tables?: string[], year?: string, month?: string): Promise<Record<string, any[]>> {
  const settings = getSettings();
  const params = new URLSearchParams();
  if (gstin) {
    const gstins = Array.isArray(gstin) ? gstin : [gstin];
    gstins.forEach(g => params.append('gstin', g));
  }
  if (tables) {
    tables.forEach(t => params.append('tables', t));
  }
  if (year) {
    params.append('year', year);
  }
  if (month) {
    params.append('month', month);
  }
  const creds = btoa(`${settings.dbProxyUser}:${settings.dbProxyPass}`);
  const res = await fetch(`${settings.dbProxyUrl}/fetch?${params.toString()}`, {
    headers: { 'Authorization': `Basic ${creds}` },
  });
  if (!res.ok) throw new Error(`DB Proxy error: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function fetchProxyClients(includeInactive = true, gstin?: string | string[]): Promise<ProxyClient[]> {
  const settings = getSettings();
  const params = new URLSearchParams();

  if (gstin) {
    const gstins = Array.isArray(gstin) ? gstin : [gstin];
    gstins.forEach(g => params.append('gstin', g));
  }

  params.append('include_inactive', includeInactive ? 'true' : 'false');

  const creds = btoa(`${settings.dbProxyUser}:${settings.dbProxyPass}`);
  const res = await fetch(`${settings.dbProxyUrl}/clients?${params.toString()}`, {
    headers: { 'Authorization': `Basic ${creds}` },
  });

  if (!res.ok) throw new Error(`DB Proxy error: ${res.status} ${res.statusText}`);

  const data = await res.json();
  return (data && data.clients) ? data.clients as ProxyClient[] : data;
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

export async function downloadMonthlyReport(gstin: string, year: string, month: string, tables?: string[]): Promise<Blob> {
  const settings = getSettings();
  const params = new URLSearchParams();
  params.append('gstin', gstin);
  params.append('year', year);
  params.append('month', month);
  if (tables && tables.length > 0) {
    tables.forEach(t => params.append('tables', t));
  }

  const creds = btoa(`${settings.dbProxyUser}:${settings.dbProxyPass}`);
  const res = await fetch(`${settings.dbProxyUrl}/report?${params.toString()}`, {
    headers: { 'Authorization': `Basic ${creds}` },
  });

  if (!res.ok) throw new Error(`DB Proxy error: ${res.status} ${res.statusText}`);
  return res.blob();
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

// --- Sandbox API Credentials ---

export async function getApiCredentials(): Promise<{ has_credentials: boolean; api_key: string; api_secret: string }> {
  const settings = getSettings();
  const res = await fetch(`${settings.serviceApiUrl}/settings/api-credentials`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function saveApiCredentials(apiKey: string, apiSecret: string): Promise<void> {
  const settings = getSettings();
  const res = await fetch(`${settings.serviceApiUrl}/settings/api-credentials`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}
