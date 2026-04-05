import { useCallback, useEffect, useRef } from 'react';
import { useApp } from '@/context/AppContext';
import { dbProxyFetch, fetchAvailablePeriods } from '@/lib/api';

// ---------------------------------------------------------------------------
// De-duplication: because useDbProxy() is mounted in many components, we keep
// a module-level guard so only ONE auto-load fires per gstin.
// ---------------------------------------------------------------------------
let _autoLoadedGstin: string | null = null;
let _inflightRefresh: string | null = null; // "gstin:year:month" currently in-flight
let _inflightPeriods: string | null = null; // gstin currently loading periods

// Map of table names to their nested array keys
const NESTED_ARRAY_KEYS: Record<string, string> = {
  'gstr1_b2b': 'invoices',
  'gstr1_b2csa': 'records',
  'gstr1_b2cs': 'records',
  'gstr1_cdnr': 'records',
  'gstr1_cdnur': 'records',
  'gstr1_exp': 'records',
  'gstr1_nil': 'records',
  'gstr1_hsn': 'records',
  'gstr1_doc_issue': 'records',
  'gstr1_b2cl': 'records',
  // TXP rows are stored under the column 'records' in DB; map accordingly
  'gstr1_txp': 'records',
  'gstr1_advance_tax': 'records',
  'gstr1_summary': 'sections',
  'gstr2a_b2b': 'records',
  'gstr2a_b2ba': 'records',
  'gstr2a_cdn': 'records',
  'gstr2a_cdna': 'records',
  'gstr2a_document': 'records',
  'gstr2a_isd': 'records',
  'gstr2a_tds': 'records',
  'gstr2b': 'records',
  'gstr3b_details': 'records',
  'gstr3b_auto_liability': 'records',
  'gstr9_auto_calculated': 'sections',
  'gstr9_table8a': 'records',
  'gstr9_details': 'sections',
  'ledger_balance': 'records',
  'ledger_cash': 'transactions',
  'ledger_itc': 'transactions',
  'ledger_liability': 'transactions',
};

function extractAndNormalizeData(tableData: any): any[] {
  if (!tableData) return [];

  // If it's already an array, return as-is
  if (Array.isArray(tableData)) return tableData;

  // If it's an object, try to extract nested array
  if (typeof tableData === 'object') {
    // Check if there's a nested array key for this table
    // The table name will be passed separately, but we need to handle the transformation
    // Try common nested array keys
    for (const key of ['records', 'invoices', 'sections', 'transactions', 'txpd', 'data']) {
      if (Array.isArray(tableData[key])) {
        return tableData[key];
      }
    }
  }

  return [];
}

function fixFieldNames(record: any): any {
  if (!record || typeof record !== 'object') return record;

  const normalized = { ...record };

  // Fix: tax_rate → rate
  if ('tax_rate' in normalized && !('rate' in normalized)) {
    normalized.rate = normalized.tax_rate;
  }

  // Fix: note_value → taxable_value
  if ('note_value' in normalized && !('taxable_value' in normalized)) {
    normalized.taxable_value = normalized.note_value;
  }

  // Convert string decimals to numbers
  const numericFields = ['taxable_value', 'invoice_value', 'note_value', 'total_taxable_value',
    'total_cgst', 'total_sgst', 'total_igst', 'cgst', 'sgst', 'igst', 'cess', 'rate',
    'total_invoices', 'ttl_rec', 'ttl_val', 'ttl_tax', 'ttl_igst', 'ttl_cgst', 'ttl_sgst', 'ttl_cess',
    'cash_igst_tax', 'cash_igst_interest', 'cash_igst_penalty', 'cash_igst_fee', 'cash_igst_other',
    'cash_igst_total', 'cash_cgst_total', 'cash_sgst_total', 'cash_cess_total',
    'itc_igst', 'itc_cgst', 'itc_sgst', 'itc_cess', 'itc_blocked_igst', 'itc_blocked_cgst', 'itc_blocked_sgst', 'itc_blocked_cess',
    'igst_amt', 'cgst_amt', 'sgst_amt', 'cess_amt', 'total_amount', 'igst_bal', 'cgst_bal', 'sgst_bal', 'cess_bal', 'total_range_balance',
    'tot_tr_amt', 'tot_rng_bal'];

  numericFields.forEach(field => {
    if (field in normalized && typeof normalized[field] === 'string') {
      const num = parseFloat(normalized[field]);
      if (!isNaN(num)) {
        normalized[field] = num;
      }
    }
  });

  return normalized;
}

export function useDbProxy() {
  const { state, dispatch, activeClient } = useApp();

  // Use refs for volatile state so callbacks never change identity due to
  // selectedPeriod / dbData changes — this is the key to stopping the loop.
  const selectedPeriodRef = useRef(state.selectedPeriod);
  selectedPeriodRef.current = state.selectedPeriod;
  const dbDataRef = useRef(state.dbData);
  dbDataRef.current = state.dbData;

  const refreshData = useCallback(async (gstin?: string, year?: string, month?: string) => {
    const g = gstin || activeClient?.gstin;
    const targetYear = year || selectedPeriodRef.current?.year;
    const targetMonth = month || selectedPeriodRef.current?.month;
    if (!g) return;

    // De-duplicate: skip if an identical request is already in-flight
    const key = `${g}:${targetYear}:${targetMonth}`;
    if (_inflightRefresh === key) return;
    _inflightRefresh = key;

    dispatch({ type: 'SET_DB_LOADING', payload: true });
    try {
      const response = await dbProxyFetch(g, undefined, targetYear, targetMonth);

      // Transform db_proxy response from nested structure to flat table structure
      const transformedData: Record<string, any[]> = {};

      if (response.clients && Array.isArray(response.clients)) {
        const clientData = response.clients.find((c: any) => c.gstin === g);
        if (clientData && clientData.tables) {
          Object.entries(clientData.tables).forEach(([tableName, tableData]: [string, any]) => {
            const rowArray = (tableData as any).rows || [];
            const flattened: any[] = [];

            rowArray.forEach((row: any) => {
              if (!row || typeof row !== 'object') return;
              const nestedKey = NESTED_ARRAY_KEYS[tableName];

              if (nestedKey && Array.isArray(row[nestedKey])) {
                row[nestedKey].forEach((item: any) => {
                  flattened.push(fixFieldNames(item));
                });
              } else {
                flattened.push(fixFieldNames(row));
              }
            });

            transformedData[tableName] = flattened;
          });
        }
      }

      dispatch({ type: 'SET_DB_DATA', payload: { gstin: g, data: transformedData } });
    } catch (err: any) {
      console.error('DB Proxy error:', err);
    } finally {
      _inflightRefresh = null;
      dispatch({ type: 'SET_DB_LOADING', payload: false });
    }
  }, [activeClient?.gstin, dispatch]);
  // NOTE: selectedPeriod removed from deps — read via ref instead

  // Stable ref so loadAvailablePeriods can call refreshData without circular deps
  const refreshDataRef = useRef(refreshData);
  refreshDataRef.current = refreshData;

  const loadAvailablePeriods = useCallback(async (gstin?: string) => {
    const g = gstin || activeClient?.gstin;
    if (!g) return;

    // De-duplicate: skip if already loading periods for this gstin
    if (_inflightPeriods === g) return;
    _inflightPeriods = g;

    try {
      const result = await fetchAvailablePeriods(g);
      const periods = result.periods || [];

      dispatch({
        type: 'SET_AVAILABLE_PERIODS',
        payload: periods,
      });

      let targetPeriod = selectedPeriodRef.current;

      if (periods.length > 0) {
        const hasSelected = targetPeriod && periods.some(
          (p) => p.year === targetPeriod?.year && p.month === targetPeriod?.month,
        );

        if (!hasSelected) {
          targetPeriod = periods[0];
          dispatch({
            type: 'SET_SELECTED_PERIOD',
            payload: periods[0],
          });
        }
      }

      // Auto-fetch data for the resolved period
      if (targetPeriod) {
        await refreshDataRef.current(g, targetPeriod.year, targetPeriod.month);
      }
    } catch (err) {
      console.error('Failed to fetch available periods:', err);
    } finally {
      _inflightPeriods = null;
    }
  }, [activeClient?.gstin, dispatch]);
  // NOTE: selectedPeriod removed from deps — read via ref instead

  // Load periods (and their data) automatically for the active client.
  // Module-level guard ensures this fires at most ONCE per gstin, even though
  // useDbProxy() is mounted in 12+ components simultaneously.
  useEffect(() => {
    const gstin = activeClient?.gstin;
    if (!gstin) return;
    if (_autoLoadedGstin === gstin) return; // already loaded for this client
    _autoLoadedGstin = gstin;
    loadAvailablePeriods(gstin);
  }, [activeClient?.gstin, loadAvailablePeriods]);

  const getData = useCallback((tableName: string): any[] => {
    if (!activeClient?.gstin) return [];
    const clientData = state.dbData[activeClient.gstin];
    if (!clientData) return [];
    return clientData[tableName] || [];
  }, [activeClient?.gstin, state.dbData]);

  return { refreshData, getData, loadAvailablePeriods, loading: state.dbLoading };
}
