import { useCallback, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import { dbProxyFetch, fetchAvailablePeriods } from '@/lib/api';

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
  'gstr1_txp': 'txpd',
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
    'total_invoices', 'ttl_rec', 'ttl_val', 'ttl_tax', 'ttl_igst', 'ttl_cgst', 'ttl_sgst', 'ttl_cess'];

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

  // Fetch available periods when active client changes
  useEffect(() => {
    if (!activeClient?.gstin) return;

    const loadPeriods = async () => {
      try {
        const result = await fetchAvailablePeriods(activeClient.gstin);
        dispatch({
          type: 'SET_AVAILABLE_PERIODS',
          payload: result.periods || [],
        });
        // Auto-select first available period
        if (result.periods && result.periods.length > 0) {
          dispatch({
            type: 'SET_SELECTED_PERIOD',
            payload: result.periods[0],
          });
        }
      } catch (err) {
        console.error('Failed to fetch available periods:', err);
      }
    };

    loadPeriods();
  }, [activeClient?.gstin, dispatch]);

  const refreshData = useCallback(async (gstin?: string) => {
    const g = gstin || activeClient?.gstin;
    if (!g) return;
    dispatch({ type: 'SET_DB_LOADING', payload: true });
    try {
      const response = await dbProxyFetch(g);

      // Transform db_proxy response from nested structure to flat table structure
      const transformedData: Record<string, any[]> = {};

      // The db_proxy response has structure: { clients: [...], filters: ..., summary: ... }
      if (response.clients && Array.isArray(response.clients)) {
        // Find client matching the GSTIN
        const clientData = response.clients.find((c: any) => c.gstin === g);
        if (clientData && clientData.tables) {
          // Flatten and normalize each table
          Object.entries(clientData.tables).forEach(([tableName, tableData]: [string, any]) => {
            // Get the array from nested structure
            const rowArray = tableData.rows || [];

            // For each row, extract its nested array (invoices, records, sections, etc.)
            const flattened: any[] = [];

            rowArray.forEach((row: any) => {
              if (!row || typeof row !== 'object') return;

              // Get the nested array key for this table
              const nestedKey = NESTED_ARRAY_KEYS[tableName];

              if (nestedKey && Array.isArray(row[nestedKey])) {
                // Extract and normalize each item in the nested array
                row[nestedKey].forEach((item: any) => {
                  flattened.push(fixFieldNames(item));
                });
              } else {
                // No nested array, push the row itself (normalized)
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
      dispatch({ type: 'SET_DB_LOADING', payload: false });
    }
  }, [activeClient?.gstin, dispatch]);

  const getData = useCallback((tableName: string): any[] => {
    if (!activeClient?.gstin) return [];
    const clientData = state.dbData[activeClient.gstin];
    if (!clientData) return [];
    return clientData[tableName] || [];
  }, [activeClient?.gstin, state.dbData]);

  return { refreshData, getData, loading: state.dbLoading };
}
