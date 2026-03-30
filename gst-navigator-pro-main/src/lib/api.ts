import { buildClientDbSnapshot, buildClientList, type DbProxyClient } from '@/lib/dashboard-data';
import type { AppSettings, ClientDbSnapshot } from '@/types/client';

export const DEFAULT_SETTINGS: AppSettings = {
  dbProxyUrl: 'http://localhost:8050',
  dbProxyUser: 'admin',
  dbProxyPass: 'root',
  serviceApiUrl: 'http://localhost:8000',
};

const LEGACY_DB_PROXY_URLS = new Set(['http://localhost:9000', 'http://127.0.0.1:9000']);

export function normalizeSettings(input?: Partial<AppSettings> | null): AppSettings {
  const incoming = input || {};
  const normalized: AppSettings = {
    dbProxyUrl: incoming.dbProxyUrl?.trim() || DEFAULT_SETTINGS.dbProxyUrl,
    dbProxyUser: incoming.dbProxyUser?.trim() || DEFAULT_SETTINGS.dbProxyUser,
    dbProxyPass: incoming.dbProxyPass?.trim() || DEFAULT_SETTINGS.dbProxyPass,
    serviceApiUrl: incoming.serviceApiUrl?.trim() || DEFAULT_SETTINGS.serviceApiUrl,
  };

  if (
    LEGACY_DB_PROXY_URLS.has(normalized.dbProxyUrl) &&
    normalized.dbProxyUser === 'admin' &&
    normalized.dbProxyPass === 'password'
  ) {
    normalized.dbProxyUrl = DEFAULT_SETTINGS.dbProxyUrl;
    normalized.dbProxyPass = DEFAULT_SETTINGS.dbProxyPass;
  }

  return normalized;
}

function getSettings(): AppSettings {
  try {
    const stored = localStorage.getItem('gst_settings');
    return normalizeSettings(stored ? JSON.parse(stored) : null);
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function buildDbProxyAuthHeader(settings: AppSettings): Record<string, string> {
  const creds = btoa(`${settings.dbProxyUser}:${settings.dbProxyPass}`);
  return { Authorization: `Basic ${creds}` };
}

function sanitizeGstin(value: string): string {
  return value.trim().toUpperCase();
}

async function buildServiceError(response: Response): Promise<Error> {
  try {
    const payload = await response.json();
    const detail = payload?.detail;
    if (typeof detail === 'string' && detail) {
      return new Error(detail);
    }
    if (detail?.message) {
      return new Error(detail.message);
    }
    if (payload?.message) {
      return new Error(payload.message);
    }
  } catch {
    // Fall back to the plain HTTP error message below.
  }

  return new Error(`HTTP ${response.status}: ${response.statusText}`);
}

// --- Service API calls ---

export async function serviceGet(path: string, token?: string | null): Promise<any> {
  const settings = getSettings();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${settings.serviceApiUrl}${path}`, { headers });
  if (res.status === 401) throw new Error('SESSION_EXPIRED');
  if (!res.ok) throw await buildServiceError(res);
  return res.json();
}

export async function servicePost(path: string, body: any, token?: string | null): Promise<any> {
  const settings = getSettings();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${settings.serviceApiUrl}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (res.status === 401) throw new Error('SESSION_EXPIRED');
  if (!res.ok) throw await buildServiceError(res);
  return res.json();
}

// --- DB Proxy calls ---

export async function dbProxyFetch(gstin?: string | string[], tables?: string[]): Promise<ClientDbSnapshot> {
  const settings = getSettings();
  const params = new URLSearchParams();
  if (gstin) {
    const gstins = (Array.isArray(gstin) ? gstin : [gstin])
      .map(sanitizeGstin)
      .filter((value) => value.length === 15);
    gstins.forEach((value) => params.append('gstin', value));

    if (gstins.length === 0) {
      throw new Error('Please provide a valid 15-character GSTIN before fetching DB data.');
    }
  }
  if (tables) {
    tables.forEach((value) => params.append('tables', value));
  }

  const res = await fetch(`${settings.dbProxyUrl}/fetch?${params.toString()}`, {
    headers: buildDbProxyAuthHeader(settings),
  });
  if (!res.ok) throw new Error(`DB Proxy error: ${res.status} ${res.statusText}`);

  const primaryGstin = Array.isArray(gstin) ? sanitizeGstin(gstin[0] || '') : (gstin ? sanitizeGstin(gstin) : undefined);
  return buildClientDbSnapshot(await res.json(), primaryGstin);
}

export async function dbProxyListClients(): Promise<DbProxyClient[]> {
  const settings = getSettings();
  const res = await fetch(`${settings.dbProxyUrl}/clients`, {
    headers: buildDbProxyAuthHeader(settings),
  });
  if (!res.ok) throw new Error(`DB Proxy client list error: ${res.status} ${res.statusText}`);
  return buildClientList(await res.json());
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
    const res = await fetch(`${settings.dbProxyUrl}/clients`, {
      headers: buildDbProxyAuthHeader(settings),
    });
    return res.ok;
  } catch {
    return false;
  }
}
