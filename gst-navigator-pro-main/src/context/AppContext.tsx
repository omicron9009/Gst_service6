import React, { createContext, useCallback, useContext, useEffect, useReducer } from 'react';
import type {
  AppAction,
  AppSettings,
  AppState,
  ClientDbSnapshot,
  DbPeriodAvailability,
  DbPeriodSelection,
  GSTClient,
} from '@/types/client';
import { DEFAULT_SETTINGS, dbProxyListClients, getSessionStatus, normalizeSettings } from '@/lib/api';

function loadClients(): GSTClient[] {
  try {
    const stored = localStorage.getItem('gst_clients');
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem('gst_settings');
    return normalizeSettings(stored ? JSON.parse(stored) : DEFAULT_SETTINGS);
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function coercePeriodSelection(
  availability: DbPeriodAvailability,
  selection?: Partial<DbPeriodSelection> | null,
): DbPeriodSelection {
  const nextYear = selection?.year && availability.monthlyYears.includes(selection.year)
    ? selection.year
    : (availability.latestMonthly?.year || null);

  const monthOptions = nextYear ? availability.monthsByYear[nextYear] || [] : [];
  const nextMonth = selection?.month && monthOptions.includes(selection.month)
    ? selection.month
    : (monthOptions[0] || null);

  const nextFinancialYear = selection?.financialYear && availability.financialYears.includes(selection.financialYear)
    ? selection.financialYear
    : (availability.latestFinancialYear || null);

  return {
    year: nextYear,
    month: nextMonth,
    financialYear: nextFinancialYear,
  };
}

const initialState: AppState = {
  clients: loadClients(),
  activeClientId: localStorage.getItem('gst_active_client') || null,
  settings: loadSettings(),
  dbData: {},
  selectedPeriods: {},
  fetchLog: [],
  dbLoading: false,
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_CLIENTS':
      return { ...state, clients: action.payload };
    case 'ADD_CLIENT':
      return { ...state, clients: [...state.clients, action.payload] };
    case 'UPDATE_CLIENT':
      return { ...state, clients: state.clients.map((client) => (client.id === action.payload.id ? action.payload : client)) };
    case 'DELETE_CLIENT': {
      const newClients = state.clients.filter((client) => client.id !== action.payload);
      const newDbData = { ...state.dbData };
      const newSelectedPeriods = { ...state.selectedPeriods };

      const removedClient = state.clients.find((client) => client.id === action.payload);
      if (removedClient) {
        delete newDbData[removedClient.gstin];
        delete newSelectedPeriods[removedClient.gstin];
      }

      return {
        ...state,
        clients: newClients,
        dbData: newDbData,
        selectedPeriods: newSelectedPeriods,
        activeClientId: state.activeClientId === action.payload ? null : state.activeClientId,
      };
    }
    case 'SET_ACTIVE_CLIENT':
      return { ...state, activeClientId: action.payload };
    case 'SET_SETTINGS':
      return { ...state, settings: action.payload };
    case 'SET_DB_DATA': {
      const currentSelection = state.selectedPeriods[action.payload.gstin];
      const nextSelection = coercePeriodSelection(action.payload.snapshot.availability, currentSelection);

      return {
        ...state,
        dbData: {
          ...state.dbData,
          [action.payload.gstin]: action.payload.snapshot,
        },
        selectedPeriods: {
          ...state.selectedPeriods,
          [action.payload.gstin]: nextSelection,
        },
      };
    }
    case 'SET_PERIOD_SELECTION': {
      const snapshot = state.dbData[action.payload.gstin];
      const currentSelection = state.selectedPeriods[action.payload.gstin];
      const merged = { ...currentSelection, ...action.payload.selection };
      const nextSelection = snapshot
        ? coercePeriodSelection(snapshot.availability, merged)
        : {
            year: merged.year || null,
            month: merged.month || null,
            financialYear: merged.financialYear || null,
          };

      return {
        ...state,
        selectedPeriods: {
          ...state.selectedPeriods,
          [action.payload.gstin]: nextSelection,
        },
      };
    }
    case 'SET_DB_LOADING':
      return { ...state, dbLoading: action.payload };
    case 'ADD_FETCH_LOG':
      return { ...state, fetchLog: [...state.fetchLog, action.payload] };
    case 'UPDATE_FETCH_LOG':
      return {
        ...state,
        fetchLog: state.fetchLog.map((entry) => (
          entry.id === action.payload.id
            ? { ...entry, status: action.payload.status, message: action.payload.message }
            : entry
        )),
      };
    case 'CLEAR_FETCH_LOG':
      return { ...state, fetchLog: [] };
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  activeClient: GSTClient | null;
  getSessionStatusForClient: (gstin: string) => 'active' | 'expired' | 'none';
  getDbSnapshotForClient: (gstin: string) => ClientDbSnapshot | null;
  getSelectedPeriodForClient: (gstin: string) => DbPeriodSelection;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const activeClient = state.clients.find((client) => client.id === state.activeClientId) || null;

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

  useEffect(() => {
    if (state.clients.length > 0) return;

    let cancelled = false;

    const hydrateClientsFromDb = async () => {
      try {
        const proxyClients = await dbProxyListClients();
        if (cancelled || proxyClients.length === 0) return;

        const importedClients: GSTClient[] = proxyClients.map((client) => ({
          id: `db:${client.gstin}`,
          label: client.label,
          username: client.username,
          gstin: client.gstin,
          sessionToken: null,
          sessionExpiry: null,
          addedAt: new Date().toISOString(),
        }));

        dispatch({ type: 'SET_CLIENTS', payload: importedClients });
        dispatch({ type: 'SET_ACTIVE_CLIENT', payload: importedClients[0]?.id || null });
      } catch {
        // Ignore proxy bootstrap failures until the user configures settings manually.
      }
    };

    hydrateClientsFromDb();

    return () => {
      cancelled = true;
    };
  }, [dispatch, state.clients.length]);

  useEffect(() => {
    state.clients.forEach(async (client) => {
      try {
        const result = await getSessionStatus(client.gstin);
        if (result?.session_active) {
          dispatch({
            type: 'UPDATE_CLIENT',
            payload: {
              ...client,
              sessionToken: result.access_token || client.sessionToken,
              sessionExpiry: result.session_expiry || client.sessionExpiry,
            },
          });
        }
      } catch {
        // Session hydration is best-effort only.
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const getSessionStatusForClient = useCallback((gstin: string): 'active' | 'expired' | 'none' => {
    const client = state.clients.find((entry) => entry.gstin === gstin);
    if (!client?.sessionToken) return 'none';
    if (!client.sessionExpiry) return 'active';
    return new Date(client.sessionExpiry) > new Date() ? 'active' : 'expired';
  }, [state.clients]);

  const getDbSnapshotForClient = useCallback((gstin: string): ClientDbSnapshot | null => {
    return state.dbData[gstin] || null;
  }, [state.dbData]);

  const getSelectedPeriodForClient = useCallback((gstin: string): DbPeriodSelection => {
    const snapshot = state.dbData[gstin];
    return snapshot
      ? coercePeriodSelection(snapshot.availability, state.selectedPeriods[gstin])
      : { year: null, month: null, financialYear: null };
  }, [state.dbData, state.selectedPeriods]);

  return (
    <AppContext.Provider value={{
      state,
      dispatch,
      activeClient,
      getSessionStatusForClient,
      getDbSnapshotForClient,
      getSelectedPeriodForClient,
    }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}
