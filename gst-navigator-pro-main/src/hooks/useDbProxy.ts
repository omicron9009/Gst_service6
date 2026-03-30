import { useCallback } from 'react';
import { useApp } from '@/context/AppContext';
import { dbProxyFetch } from '@/lib/api';
import type { ClientDbSnapshot, DbPeriodAvailability, DbPeriodSelection } from '@/types/client';

type RowMeta = {
  periodKind?: 'monthly' | 'financial_year' | 'global';
  year?: string;
  month?: string;
  financialYear?: string;
  updatedAt?: string | null;
};

const EMPTY_SNAPSHOT: ClientDbSnapshot = {
  datasets: {},
  availability: {
    monthlyYears: [],
    monthsByYear: {},
    financialYears: [],
    latestMonthly: null,
    latestFinancialYear: null,
  },
  fetchedAt: '',
};

const EMPTY_SELECTION: DbPeriodSelection = {
  year: null,
  month: null,
  financialYear: null,
};

function isValidGstin(value?: string | null): boolean {
  const gstin = (value || '').trim().toUpperCase();
  return gstin.length === 15;
}

function matchesSelectedPeriod(row: any, selection: DbPeriodSelection): boolean {
  const meta = (row as { __meta?: RowMeta }).__meta;
  if (!meta || meta.periodKind === 'global' || !meta.periodKind) return true;

  if (meta.periodKind === 'monthly') {
    return meta.year === selection.year && meta.month === selection.month;
  }

  if (meta.periodKind === 'financial_year') {
    return meta.financialYear === selection.financialYear;
  }

  return true;
}

function maxUpdatedAt(rows: any[]): string | undefined {
  return rows
    .map((row) => (row as { __meta?: RowMeta }).__meta?.updatedAt)
    .filter((value): value is string => !!value)
    .sort()
    .at(-1);
}

export function useDbProxy() {
  const {
    dispatch,
    activeClient,
    getDbSnapshotForClient,
    getSelectedPeriodForClient,
    state,
  } = useApp();

  const refreshData = useCallback(async (gstin?: string) => {
    const resolvedGstin = gstin || activeClient?.gstin;
    if (!resolvedGstin || !isValidGstin(resolvedGstin)) return;

    dispatch({ type: 'SET_DB_LOADING', payload: true });
    try {
      const snapshot = await dbProxyFetch(resolvedGstin);
      dispatch({ type: 'SET_DB_DATA', payload: { gstin: resolvedGstin, snapshot } });
    } catch (err: any) {
      console.error('DB Proxy error:', err);
    } finally {
      dispatch({ type: 'SET_DB_LOADING', payload: false });
    }
  }, [activeClient?.gstin, dispatch]);

  const snapshot = activeClient?.gstin ? (getDbSnapshotForClient(activeClient.gstin) || EMPTY_SNAPSHOT) : EMPTY_SNAPSHOT;
  const selection = activeClient?.gstin ? getSelectedPeriodForClient(activeClient.gstin) : EMPTY_SELECTION;

  const getData = useCallback((datasetName: string): any[] => {
    if (!activeClient?.gstin) return [];
    const rows = getDbSnapshotForClient(activeClient.gstin)?.datasets[datasetName] || [];
    return rows.filter((row) => matchesSelectedPeriod(row, getSelectedPeriodForClient(activeClient.gstin)));
  }, [activeClient?.gstin, getDbSnapshotForClient, getSelectedPeriodForClient]);

  const getLastUpdated = useCallback((datasetNames: string | string[]): string | undefined => {
    if (!activeClient?.gstin) return undefined;
    const names = Array.isArray(datasetNames) ? datasetNames : [datasetNames];
    const rows = names.flatMap((name) => getDbSnapshotForClient(activeClient.gstin)?.datasets[name] || []);
    return maxUpdatedAt(rows);
  }, [activeClient?.gstin, getDbSnapshotForClient]);

  const setPeriodSelection = useCallback((nextSelection: Partial<DbPeriodSelection>, gstin?: string) => {
    const resolvedGstin = gstin || activeClient?.gstin;
    if (!resolvedGstin) return;
    dispatch({ type: 'SET_PERIOD_SELECTION', payload: { gstin: resolvedGstin, selection: nextSelection } });
  }, [activeClient?.gstin, dispatch]);

  return {
    refreshData,
    getData,
    getLastUpdated,
    setPeriodSelection,
    loading: state.dbLoading,
    snapshot,
    availability: snapshot.availability as DbPeriodAvailability,
    selection,
  };
}
