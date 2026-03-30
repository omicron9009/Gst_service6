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

export interface DbPeriodAvailability {
  monthlyYears: string[];
  monthsByYear: Record<string, string[]>;
  financialYears: string[];
  latestMonthly: { year: string; month: string } | null;
  latestFinancialYear: string | null;
}

export interface DbPeriodSelection {
  year: string | null;
  month: string | null;
  financialYear: string | null;
}

export interface ClientDbSnapshot {
  datasets: Record<string, any[]>;
  availability: DbPeriodAvailability;
  fetchedAt: string;
}

export interface AppState {
  clients: GSTClient[];
  activeClientId: string | null;
  settings: AppSettings;
  dbData: Record<string, ClientDbSnapshot>;
  selectedPeriods: Record<string, DbPeriodSelection>;
  fetchLog: FetchLogEntry[];
  dbLoading: boolean;
}

export type AppAction =
  | { type: 'SET_CLIENTS'; payload: GSTClient[] }
  | { type: 'ADD_CLIENT'; payload: GSTClient }
  | { type: 'UPDATE_CLIENT'; payload: GSTClient }
  | { type: 'DELETE_CLIENT'; payload: string }
  | { type: 'SET_ACTIVE_CLIENT'; payload: string | null }
  | { type: 'SET_SETTINGS'; payload: AppSettings }
  | { type: 'SET_DB_DATA'; payload: { gstin: string; snapshot: ClientDbSnapshot } }
  | { type: 'SET_PERIOD_SELECTION'; payload: { gstin: string; selection: Partial<DbPeriodSelection> } }
  | { type: 'SET_DB_LOADING'; payload: boolean }
  | { type: 'ADD_FETCH_LOG'; payload: FetchLogEntry }
  | { type: 'UPDATE_FETCH_LOG'; payload: { id: string; status: FetchLogEntry['status']; message?: string } }
  | { type: 'CLEAR_FETCH_LOG' };
