import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import type { AppState, AppAction, GSTClient, AppSettings, FetchLogEntry } from '@/types/client';
import { getSessionStatus } from '@/lib/api';

const DEFAULT_SETTINGS: AppSettings = {
  dbProxyUrl: 'http://localhost:9000',
  dbProxyUser: 'admin',
  dbProxyPass: 'password',
  serviceApiUrl: 'http://localhost:8000',
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
    return stored ? JSON.parse(stored) : DEFAULT_SETTINGS;
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

  // Check session status on mount
  useEffect(() => {
    state.clients.forEach(async (client) => {
      try {
        const result = await getSessionStatus(client.gstin);
        if (result?.session_active) {
          dispatch({
            type: 'UPDATE_CLIENT',
            payload: { ...client, sessionToken: result.access_token || client.sessionToken, sessionExpiry: result.session_expiry || client.sessionExpiry }
          });
        }
      } catch {
        // silently fail
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
