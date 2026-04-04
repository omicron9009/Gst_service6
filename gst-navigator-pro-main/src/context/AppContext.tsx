import React, { createContext, useContext, useReducer, useEffect, useCallback, useRef } from 'react';
import type { AppState, AppAction, GSTClient, AppSettings, FetchLogEntry, ProxyClient } from '@/types/client';
import { fetchProxyClients, getSessionStatus } from '@/lib/api';

const host = window.location.hostname;

const DEFAULT_SETTINGS: AppSettings = {
  dbProxyUrl: `http://${host}:8050`,
  dbProxyUser: 'admin',
  dbProxyPass: 'root',
  serviceApiUrl: `http://${host}:8000`,
};

function loadClients(): GSTClient[] {
  try {
    const stored = localStorage.getItem('gst_clients');
    return stored ? JSON.parse(stored) : [];
  } catch { return []; }
}

function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem('gst_settings');
    if (!stored) return DEFAULT_SETTINGS;

    const parsed: Partial<AppSettings> = JSON.parse(stored);

    // Backward compatibility: ensure credentials and URL align with current proxy defaults.
    const safeSettings: AppSettings = {
      dbProxyUrl: parsed.dbProxyUrl || DEFAULT_SETTINGS.dbProxyUrl,
      dbProxyUser: parsed.dbProxyUser || DEFAULT_SETTINGS.dbProxyUser,
      dbProxyPass: parsed.dbProxyPass || DEFAULT_SETTINGS.dbProxyPass,
      serviceApiUrl: parsed.serviceApiUrl || DEFAULT_SETTINGS.serviceApiUrl,
    };

    // If an old password was persisted (e.g., "password"), replace with current default "root".
    if (safeSettings.dbProxyPass === 'password') {
      safeSettings.dbProxyPass = DEFAULT_SETTINGS.dbProxyPass;
    }

    return safeSettings;
  } catch { return DEFAULT_SETTINGS; }
}

const initialState: AppState = {
  clients: loadClients(),
  activeClientId: localStorage.getItem('gst_active_client') || null,
  settings: loadSettings(),
  dbData: {},
  fetchLog: [],
  dbLoading: false,
  selectedPeriod: null,
  availablePeriods: [],
};

function mapProxyClients(
  proxyClients: ProxyClient[],
  existingByGstin: Map<string, GSTClient>,
): GSTClient[] {
  const normalizeGstin = (gstin: string) => (gstin || '').trim().toUpperCase();
  const existingByNormalizedGstin = new Map(
    Array.from(existingByGstin.entries()).map(([gstin, client]) => [normalizeGstin(gstin), client]),
  );

  return proxyClients.map((client) => {
    const existing = existingByNormalizedGstin.get(normalizeGstin(client.gstin));
    const label = existing?.label
      || client.trade_name
      || client.legal_name
      || client.username
      || client.gstin;

    // Preserve username captured locally when the proxy does not return one; otherwise OTP payload is empty.
    const username = client.username || existing?.username || '';

    return {
      id: String(client.id),
      label,
      username,
      gstin: client.gstin,
      tradeName: client.trade_name ?? null,
      legalName: client.legal_name ?? null,
      isActive: client.is_active ?? true,
      sessionToken: existing?.sessionToken ?? null,
      sessionExpiry: existing?.sessionExpiry ?? null,
      addedAt: existing?.addedAt ?? null,
    } satisfies GSTClient;
  });
}

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_CLIENTS':
      return { ...state, clients: action.payload };
    case 'ADD_CLIENT':
      return { ...state, clients: [...state.clients, action.payload] };
    case 'UPDATE_CLIENT':
      return { ...state, clients: state.clients.map(c => c.id === action.payload.id ? action.payload : c) };
    case 'DELETE_CLIENT': {
      const newClients = state.clients.filter(c => c.id !== action.payload);
      return {
        ...state,
        clients: newClients,
        activeClientId: state.activeClientId === action.payload ? null : state.activeClientId,
      };
    }
    case 'SET_ACTIVE_CLIENT':
      return { ...state, activeClientId: action.payload };
    case 'SET_SETTINGS':
      return { ...state, settings: action.payload };
    case 'SET_DB_DATA':
      return { ...state, dbData: { ...state.dbData, [action.payload.gstin]: action.payload.data } };
    case 'SET_DB_LOADING':
      return { ...state, dbLoading: action.payload };
    case 'ADD_FETCH_LOG':
      return { ...state, fetchLog: [...state.fetchLog, action.payload] };
    case 'UPDATE_FETCH_LOG':
      return {
        ...state,
        fetchLog: state.fetchLog.map(l =>
          l.id === action.payload.id
            ? { ...l, status: action.payload.status, message: action.payload.message }
            : l
        ),
      };
    case 'CLEAR_FETCH_LOG':
      return { ...state, fetchLog: [] };
    case 'SET_SELECTED_PERIOD':
      return { ...state, selectedPeriod: action.payload };
    case 'SET_AVAILABLE_PERIODS':
      return { ...state, availablePeriods: action.payload };
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  activeClient: GSTClient | null;
  getSessionStatusForClient: (gstin: string) => 'active' | 'expired' | 'none';
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const checkedSessions = useRef<Set<string>>(new Set());

  const activeClient = state.clients.find(c => c.id === state.activeClientId) || null;

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem('gst_clients', JSON.stringify(state.clients));
  }, [state.clients]);

  useEffect(() => {
    if (state.activeClientId) {
      localStorage.setItem('gst_active_client', state.activeClientId);
    } else {
      localStorage.removeItem('gst_active_client');
    }
  }, [state.activeClientId]);

  useEffect(() => {
    localStorage.setItem('gst_settings', JSON.stringify(state.settings));
  }, [state.settings]);

  // Load clients from DB proxy
  useEffect(() => {
    let cancelled = false;

    const loadClients = async () => {
      try {
        const proxyClients = await fetchProxyClients(true);
        const existingByGstin = new Map(state.clients.map(c => [c.gstin, c]));
        const normalized = mapProxyClients(proxyClients, existingByGstin);

        // Preserve local-only clients (added via modal but not yet OTP-verified / not in DB)
        const proxyGstins = new Set(proxyClients.map(c => (c.gstin || '').trim().toUpperCase()));
        const localOnly = state.clients.filter(c => !proxyGstins.has((c.gstin || '').trim().toUpperCase()));
        const merged = [...normalized, ...localOnly];

        if (cancelled) return;

        dispatch({ type: 'SET_CLIENTS', payload: merged });

        if (!state.activeClientId && merged.length > 0) {
          dispatch({ type: 'SET_ACTIVE_CLIENT', payload: merged[0].id });
        }
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('Failed to fetch clients from DB proxy', err);
      }
    };

    loadClients();

    return () => {
      cancelled = true;
    };
    // We intentionally exclude state.clients from deps to avoid refetch loops; credentials changes re-trigger fetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.settings.dbProxyUrl, state.settings.dbProxyUser, state.settings.dbProxyPass]);

  // Check session status once per client
  useEffect(() => {
    state.clients.forEach(async (client) => {
      if (checkedSessions.current.has(client.gstin)) return;
      checkedSessions.current.add(client.gstin);

      try {
        const result = await getSessionStatus(client.gstin);
        if (result?.active) {
          dispatch({
            type: 'UPDATE_CLIENT',
            payload: { ...client, sessionToken: result.access_token || client.sessionToken, sessionExpiry: result.session_expiry || client.sessionExpiry }
          });
        }
      } catch {
        // silently fail
      }
    });
  }, [state.clients]);

  const getSessionStatusForClient = useCallback((gstin: string): 'active' | 'expired' | 'none' => {
    const client = state.clients.find(c => c.gstin === gstin);
    if (!client?.sessionToken) return 'none';
    if (!client.sessionExpiry) return 'active';
    return new Date(client.sessionExpiry) > new Date() ? 'active' : 'expired';
  }, [state.clients]);

  return (
    <AppContext.Provider value={{ state, dispatch, activeClient, getSessionStatusForClient }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
