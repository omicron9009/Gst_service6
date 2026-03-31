export interface GSTClient {
  id: string;
  label: string;
  username: string;
  gstin: string;
  sessionToken: string | null;
  sessionExpiry: string | null;
  addedAt: string;
}

export interface AppSettings {
  dbProxyUrl: string;
  dbProxyUser: string;
  dbProxyPass: string;
  serviceApiUrl: string;
}

export type SessionStatus = 'active' | 'expired' | 'none';

export interface FetchLogEntry {
  id: string;
  group: string;
  endpoint: string;
  status: 'pending' | 'fetching' | 'done' | 'error';
  message?: string;
  timestamp: string;
}

export interface Period {
  year: string;
  month: string;
}

export interface AppState {
  clients: GSTClient[];
  activeClientId: string | null;
  settings: AppSettings;
  dbData: Record<string, Record<string, any[]>>;
  fetchLog: FetchLogEntry[];
  dbLoading: boolean;
  selectedPeriod: Period | null;
  availablePeriods: Period[];
}

export type AppAction =
  | { type: 'SET_CLIENTS'; payload: GSTClient[] }
  | { type: 'ADD_CLIENT'; payload: GSTClient }
  | { type: 'UPDATE_CLIENT'; payload: GSTClient }
  | { type: 'DELETE_CLIENT'; payload: string }
  | { type: 'SET_ACTIVE_CLIENT'; payload: string | null }
  | { type: 'SET_SETTINGS'; payload: AppSettings }
  | { type: 'SET_DB_DATA'; payload: { gstin: string; data: Record<string, any[]> } }
  | { type: 'SET_DB_LOADING'; payload: boolean }
  | { type: 'ADD_FETCH_LOG'; payload: FetchLogEntry }
  | { type: 'UPDATE_FETCH_LOG'; payload: { id: string; status: FetchLogEntry['status']; message?: string } }
  | { type: 'CLEAR_FETCH_LOG' }
  | { type: 'SET_SELECTED_PERIOD'; payload: Period | null }
  | { type: 'SET_AVAILABLE_PERIODS'; payload: Period[] };
