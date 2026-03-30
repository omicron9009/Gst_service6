import type { ClientDbSnapshot, DbPeriodAvailability } from '@/types/client';

type ProxyTablePayload = {
  row_count?: number;
  rows?: any[];
};

type ProxyClientPayload = {
  id?: number;
  gstin?: string;
  username?: string | null;
  trade_name?: string | null;
  legal_name?: string | null;
  is_active?: boolean;
  tables?: Record<string, ProxyTablePayload>;
};

type ProxyFetchPayload = {
  clients?: ProxyClientPayload[];
};

type RowMeta = {
  sourceTable: string;
  periodKind: 'monthly' | 'financial_year' | 'global';
  year?: string;
  month?: string;
  financialYear?: string;
  updatedAt?: string | null;
};

export type DbProxyClient = {
  gstin: string;
  username: string;
  label: string;
};

const EMPTY_AVAILABILITY: DbPeriodAvailability = {
  monthlyYears: [],
  monthsByYear: {},
  financialYears: [],
  latestMonthly: null,
  latestFinancialYear: null,
};

function asArray<T = any>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function asRecord(value: unknown): Record<string, any> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, any>) : {};
}

function toNumber(value: unknown, fallback = 0): number {
  if (value === null || value === undefined || value === '') return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toText(value: unknown): string {
  return value === null || value === undefined ? '' : String(value).trim();
}

function parseUpdateRank(row: Record<string, any>): number {
  const updatedAt = row.updated_at || row.fetched_at || row.created_at;
  const parsed = Date.parse(String(updatedAt || ''));
  if (Number.isFinite(parsed)) return parsed;
  return toNumber(row.id);
}

function getRowKey(tableName: string, row: Record<string, any>): string {
  switch (tableName) {
    case 'gstr1_advance_tax':
    case 'gstr1_b2csa':
    case 'gstr1_b2cs':
    case 'gstr1_doc_issue':
    case 'gstr1_hsn':
    case 'gstr1_nil':
    case 'gstr1_b2cl':
    case 'gstr1_cdnur':
    case 'gstr1_exp':
    case 'gstr2a_b2b':
    case 'gstr2a_document':
    case 'gstr2a_tds':
    case 'gstr3b_details':
    case 'gstr3b_auto_liability':
    case 'ledger_balance':
      return [row.client_id, row.year, row.month].map(toText).join('|');
    case 'gstr1_b2b':
      return [
        row.client_id,
        row.year,
        row.month,
        row.filter_action_required,
        row.filter_from_date,
        row.filter_counterparty_gstin,
      ].map(toText).join('|');
    case 'gstr1_summary':
      return [row.client_id, row.year, row.month, row.summary_type].map(toText).join('|');
    case 'gstr1_cdnr':
      return [row.client_id, row.year, row.month, row.filter_action_required, row.filter_from_date].map(toText).join('|');
    case 'gstr1_txp':
      return [
        row.client_id,
        row.year,
        row.month,
        row.filter_counterparty_gstin,
        row.filter_action_required,
        row.filter_from_date,
      ].map(toText).join('|');
    case 'gstr2a_b2ba':
    case 'gstr2a_cdna':
    case 'gstr2a_isd':
      return [row.client_id, row.year, row.month, row.filter_counterparty_gstin].map(toText).join('|');
    case 'gstr2a_cdn':
      return [row.client_id, row.year, row.month, row.filter_counterparty_gstin, row.filter_from_date].map(toText).join('|');
    case 'gstr2b':
      return [row.client_id, row.year, row.month, row.response_type, row.file_number].map(toText).join('|');
    case 'gstr2b_regen_status':
      return [row.client_id, row.reference_id].map(toText).join('|');
    case 'gstr9_auto_calculated':
    case 'gstr9_details':
      return [row.client_id, row.financial_year].map(toText).join('|');
    case 'gstr9_table8a':
      return [row.client_id, row.financial_year, row.file_number].map(toText).join('|');
    case 'ledger_cash':
    case 'ledger_itc':
      return [row.client_id, row.from_date, row.to_date].map(toText).join('|');
    case 'ledger_liability':
      return [row.client_id, row.year, row.month, row.from_date, row.to_date].map(toText).join('|');
    case 'gst_return_status':
      return [row.client_id, row.year, row.month, row.reference_id].map(toText).join('|');
    default:
      return toText(row.id);
  }
}

function dedupeRows(tableName: string, rows: any[]): Record<string, any>[] {
  const seen = new Map<string, Record<string, any>>();

  for (const rawRow of rows) {
    const row = asRecord(rawRow);
    const key = getRowKey(tableName, row);
    const previous = seen.get(key);

    // Prefer usable rows over failed snapshots for the same logical period key.
    if (!previous) {
      seen.set(key, row);
      continue;
    }

    const currentUsable = isUsableRow(row);
    const previousUsable = isUsableRow(previous);

    if (currentUsable && !previousUsable) {
      seen.set(key, row);
      continue;
    }

    if (!currentUsable && previousUsable) {
      continue;
    }

    if (parseUpdateRank(row) >= parseUpdateRank(previous)) {
      seen.set(key, row);
    }
  }

  return Array.from(seen.values());
}

function isUsableRow(row: Record<string, any>): boolean {
  const upstreamStatus = row.upstream_status_code;
  if (upstreamStatus !== null && upstreamStatus !== undefined && toNumber(upstreamStatus) >= 400) {
    return false;
  }

  return toText(row.status_cd) !== '0';
}

function getRowMeta(sourceTable: string, row: Record<string, any>): RowMeta {
  const updatedAt = toText(row.updated_at || row.fetched_at || row.created_at) || null;

  if (toText(row.financial_year)) {
    return {
      sourceTable,
      periodKind: 'financial_year',
      financialYear: toText(row.financial_year),
      updatedAt,
    };
  }

  let year = toText(row.year);
  let month = toText(row.month);

  if ((!year || !month) && toText(row.from_date)) {
    const match = /^(\d{4})-(\d{2})/.exec(toText(row.from_date));
    if (match) {
      year = match[1];
      month = match[2];
    }
  }

  if (year && month) {
    return {
      sourceTable,
      periodKind: 'monthly',
      year,
      month,
      updatedAt,
    };
  }

  return {
    sourceTable,
    periodKind: 'global',
    updatedAt,
  };
}

function attachMeta<T extends Record<string, any>>(record: T, meta: RowMeta): T {
  Object.defineProperty(record, '__meta', {
    value: meta,
    enumerable: false,
    configurable: true,
  });
  return record;
}

function sortYearsDesc(values: Iterable<string>): string[] {
  return Array.from(new Set(values))
    .filter(Boolean)
    .sort((left, right) => toNumber(right) - toNumber(left));
}

function sortFinancialYearsDesc(values: Iterable<string>): string[] {
  return Array.from(new Set(values))
    .filter(Boolean)
    .sort((left, right) => {
      const leftStart = toNumber(left.split('-')[0]);
      const rightStart = toNumber(right.split('-')[0]);
      return rightStart - leftStart;
    });
}

function finalizeAvailability(
  monthlyYears: Set<string>,
  monthsByYear: Map<string, Set<string>>,
  financialYears: Set<string>,
): DbPeriodAvailability {
  const monthlyYearsSorted = sortYearsDesc(monthlyYears);
  const monthsByYearSorted: Record<string, string[]> = {};

  monthlyYearsSorted.forEach((year) => {
    monthsByYearSorted[year] = sortYearsDesc(monthsByYear.get(year) || []);
  });

  const financialYearsSorted = sortFinancialYearsDesc(financialYears);

  return {
    monthlyYears: monthlyYearsSorted,
    monthsByYear: monthsByYearSorted,
    financialYears: financialYearsSorted,
    latestMonthly: monthlyYearsSorted.length
      ? {
          year: monthlyYearsSorted[0],
          month: monthsByYearSorted[monthlyYearsSorted[0]]?.[0] || null,
        }
      : null,
    latestFinancialYear: financialYearsSorted[0] || null,
  };
}

function registerAvailability(
  monthlyYears: Set<string>,
  monthsByYear: Map<string, Set<string>>,
  financialYears: Set<string>,
  meta: RowMeta,
): void {
  if (meta.periodKind === 'monthly' && meta.year && meta.month) {
    monthlyYears.add(meta.year);
    if (!monthsByYear.has(meta.year)) {
      monthsByYear.set(meta.year, new Set<string>());
    }
    monthsByYear.get(meta.year)?.add(meta.month);
    return;
  }

  if (meta.periodKind === 'financial_year' && meta.financialYear) {
    financialYears.add(meta.financialYear);
  }
}

function summarizeItemList(items: unknown, fallback: Record<string, any> = {}): Record<string, any> {
  const itemList = asArray(items).map(asRecord);
  const rateValues = new Set<string>();

  let taxableValue = 0;
  let igst = 0;
  let cgst = 0;
  let sgst = 0;
  let cess = 0;

  itemList.forEach((item) => {
    const rate = item.tax_rate ?? item.rate ?? item.rt;
    if (rate !== null && rate !== undefined && String(rate) !== '') {
      rateValues.add(String(rate));
    }
    taxableValue += toNumber(item.taxable_value ?? item.txval);
    igst += toNumber(item.igst ?? item.iamt);
    cgst += toNumber(item.cgst ?? item.camt);
    sgst += toNumber(item.sgst ?? item.samt);
    cess += toNumber(item.cess ?? item.csamt);
  });

  if (itemList.length === 0) {
    const fallbackRate = fallback.tax_rate ?? fallback.rate ?? fallback.rt;
    if (fallbackRate !== null && fallbackRate !== undefined && String(fallbackRate) !== '') {
      rateValues.add(String(fallbackRate));
    }
    taxableValue = toNumber(fallback.taxable_value ?? fallback.txval);
    igst = toNumber(fallback.igst ?? fallback.iamt);
    cgst = toNumber(fallback.cgst ?? fallback.camt);
    sgst = toNumber(fallback.sgst ?? fallback.samt);
    cess = toNumber(fallback.cess ?? fallback.csamt);
  }

  const rateList = Array.from(rateValues);

  return {
    item_count: itemList.length,
    rate: rateList.length === 1 ? rateList[0] : '',
    rate_label: rateList.join(', '),
    taxable_value: taxableValue,
    igst,
    cgst,
    sgst,
    cess,
    total_tax: igst + cgst + sgst + cess,
  };
}

function pushDatasetRow(
  datasets: Record<string, any[]>,
  datasetName: string,
  row: Record<string, any>,
  meta: RowMeta,
): void {
  if (!datasets[datasetName]) datasets[datasetName] = [];
  datasets[datasetName].push(attachMeta(row, meta));
}

function pushRowsFromRecords(
  datasets: Record<string, any[]>,
  datasetName: string,
  records: unknown,
  meta: RowMeta,
  mapper?: (record: Record<string, any>) => Record<string, any>,
): void {
  asArray(records).forEach((recordValue) => {
    const record = asRecord(recordValue);
    pushDatasetRow(datasets, datasetName, mapper ? mapper(record) : record, meta);
  });
}

function normalizeGstr1AdvanceTaxRows(
  datasets: Record<string, any[]>,
  row: Record<string, any>,
  meta: RowMeta,
): void {
  asArray(row.records).forEach((entryValue) => {
    const entry = asRecord(entryValue);
    const items = asArray(entry.items).map(asRecord);

    if (items.length === 0) {
      pushDatasetRow(datasets, 'gstr1_at', {
        place_of_supply: entry.place_of_supply,
        supply_type: entry.supply_type,
        rate: '',
        taxable_value: 0,
        igst: 0,
        cgst: 0,
        sgst: 0,
        cess: 0,
      }, meta);
      return;
    }

    items.forEach((item) => {
      pushDatasetRow(datasets, 'gstr1_at', {
        place_of_supply: entry.place_of_supply,
        supply_type: entry.supply_type,
        rate: item.rate ?? item.tax_rate ?? '',
        taxable_value: toNumber(item.taxable_value),
        igst: toNumber(item.igst),
        cgst: toNumber(item.cgst),
        sgst: toNumber(item.sgst),
        cess: toNumber(item.cess),
      }, meta);
    });
  });
}

function normalizeGstr1ItemizedRecord(record: Record<string, any>): Record<string, any> {
  const summary = summarizeItemList(record.items, record);
  return {
    ...record,
    ...summary,
    rate: record.rate ?? record.tax_rate ?? record.rt ?? summary.rate,
    tax_rate: record.tax_rate ?? record.rate ?? record.rt ?? summary.rate,
  };
}

function normalizeGstr1TxpRows(
  datasets: Record<string, any[]>,
  row: Record<string, any>,
  meta: RowMeta,
): void {
  asArray(row.records).forEach((entryValue) => {
    const entry = asRecord(entryValue);
    const items = asArray(entry.items).map(asRecord);

    if (items.length === 0) {
      const totals = asRecord(entry.totals);
      pushDatasetRow(datasets, 'gstr1_txp', {
        place_of_supply: entry.place_of_supply || entry.pos,
        supply_type: entry.supply_type,
        rate: '',
        advance_amount: toNumber(totals.advance_amount),
        igst: toNumber(totals.igst),
        cgst: toNumber(totals.cgst),
        sgst: toNumber(totals.sgst),
        cess: toNumber(totals.cess),
        total_tax: toNumber(totals.total_tax),
        flag: entry.flag,
        action_required: !!entry.action_required,
      }, meta);
      return;
    }

    items.forEach((item) => {
      const mapped = {
        place_of_supply: entry.place_of_supply || entry.pos,
        supply_type: entry.supply_type,
        rate: item.tax_rate ?? item.rate ?? '',
        advance_amount: toNumber(item.advance_amount),
        igst: toNumber(item.igst),
        cgst: toNumber(item.cgst),
        sgst: toNumber(item.sgst),
        cess: toNumber(item.cess),
        total_tax: toNumber(item.igst) + toNumber(item.cgst) + toNumber(item.sgst) + toNumber(item.cess),
        flag: entry.flag,
        action_required: !!entry.action_required,
      };
      pushDatasetRow(datasets, 'gstr1_txp', mapped, meta);
    });
  });
}

function normalizeGstr1B2csRecord(record: Record<string, any>): Record<string, any> {
  return {
    ...record,
    place_of_supply: record.place_of_supply || record.pos || '',
    supply_type: record.supply_type || '',
    invoice_type: record.invoice_type || '',
    tax_rate: record.tax_rate ?? record.rt ?? null,
    taxable_value: toNumber(record.taxable_value ?? record.txval),
    igst: toNumber(record.igst ?? record.iamt),
    cgst: toNumber(record.cgst ?? record.camt),
    sgst: toNumber(record.sgst ?? record.samt),
    cess: toNumber(record.cess ?? record.csamt),
    flag: record.flag || '',
  };
}

function normalizeGstr2aItemizedRecord(record: Record<string, any>): Record<string, any> {
  const summary = summarizeItemList(record.items, record);
  return {
    ...record,
    ...summary,
    tax_rate: record.tax_rate ?? record.rate ?? record.rt ?? summary.rate,
  };
}

function normalizeGstr2aDocumentRows(
  datasets: Record<string, any[]>,
  row: Record<string, any>,
  meta: RowMeta,
): void {
  const sections: Array<[string, unknown]> = [
    ['B2B', row.b2b],
    ['B2BA', row.b2ba],
    ['CDN', row.cdn],
  ];

  sections.forEach(([section, entries]) => {
    asArray(entries).forEach((entryValue) => {
      const entry = normalizeGstr2aItemizedRecord(asRecord(entryValue));
      pushDatasetRow(datasets, 'gstr2a_document', {
        ...entry,
        document_section: section,
      }, meta);
    });
  });
}

function normalizeGstr2aTdsRows(
  datasets: Record<string, any[]>,
  row: Record<string, any>,
  meta: RowMeta,
): void {
  asArray(row.tds_entries).forEach((entryValue) => {
    const entry = asRecord(entryValue);
    const credit = asRecord(entry.tds_credit);
    pushDatasetRow(datasets, 'gstr2a_tds', {
      ...entry,
      igst: toNumber(credit.igst),
      cgst: toNumber(credit.cgst),
      sgst: toNumber(credit.sgst),
      total_tds_credit: toNumber(credit.total),
    }, meta);
  });
}

function normalizeSupplierDocumentRows(
  datasets: Record<string, any[]>,
  datasetName: string,
  groups: unknown,
  section: string,
  meta: RowMeta,
): void {
  asArray(groups).forEach((groupValue) => {
    const group = asRecord(groupValue);
    asArray(group.documents).forEach((documentValue) => {
      const document = asRecord(documentValue);
      pushDatasetRow(datasets, datasetName, {
        ...document,
        document_section: section,
        supplier_gstin: group.supplier_gstin,
        filing_date: group.filing_date,
        return_period: group.return_period,
      }, meta);
    });
  });
}

function normalizeGstr2bDocumentRows(
  datasets: Record<string, any[]>,
  row: Record<string, any>,
  meta: RowMeta,
): void {
  const invoiceSections: Array<[string, unknown]> = [
    ['B2B', asRecord(row.b2b).invoices],
    ['B2BA', asRecord(row.b2ba).invoices],
  ];

  invoiceSections.forEach(([section, entries]) => {
    pushRowsFromRecords(datasets, 'gstr2b_documents', entries, meta, (record) => {
      const summary = summarizeItemList(record.items, record);
      return {
        ...record,
        ...summary,
        document_section: section,
        supplier_gstin: record.supplier_gstin || record.ctin || '',
        invoice_number: record.invoice_number || record.invnum || '',
        invoice_date: record.invoice_date || record.invdt || '',
        invoice_type: record.invoice_type || '',
        invoice_value: toNumber(record.invoice_value ?? record.val),
        place_of_supply: record.place_of_supply || record.pos || '',
        reverse_charge: record.reverse_charge || record.rev || '',
      };
    });
  });

  const noteSections: Array<[string, unknown]> = [
    ['CDNR', asRecord(row.cdnr).notes],
    ['CDNRA', asRecord(row.cdnra).notes],
  ];

  noteSections.forEach(([section, entries]) => {
    pushRowsFromRecords(datasets, 'gstr2b_documents', entries, meta, (record) => {
      const summary = summarizeItemList(record.items, record);
      return {
        ...record,
        ...summary,
        document_section: section,
        supplier_gstin: record.supplier_gstin || record.ctin || '',
        note_number: record.note_number || record.ntnum || '',
        note_date: record.note_date || record.ntdt || '',
        note_type: record.note_type || record.ntty || '',
        note_value: toNumber(record.note_value ?? record.val),
        place_of_supply: record.place_of_supply || record.pos || '',
        reverse_charge: record.reverse_charge || record.rev || '',
      };
    });
  });

  pushRowsFromRecords(datasets, 'gstr2b_documents', asRecord(row.isd).entries, meta, (record) => ({
    ...record,
    document_section: 'ISD',
    supplier_gstin: record.isd_gstin || record.distributor_gstin || '',
    document_number: record.document_number || record.doc_number || '',
    document_date: record.document_date || record.doc_date || '',
    document_type: record.document_type || record.doc_type || '',
    itc_available: record.itc_available ?? record.itc_eligible ?? '',
    igst: toNumber(record.igst),
    cgst: toNumber(record.cgst),
    sgst: toNumber(record.sgst),
    cess: toNumber(record.cess),
    total_tax: toNumber(record.igst) + toNumber(record.cgst) + toNumber(record.sgst) + toNumber(record.cess),
  }));
}

function parseMaybeJsonObject(value: unknown): Record<string, any> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, any>;
  }

  if (typeof value !== 'string') {
    return {};
  }

  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, any>)
      : {};
  } catch {
    return {};
  }
}

function normalizeDashboardDatasets(client: ProxyClientPayload): ClientDbSnapshot {
  const datasets: Record<string, any[]> = {};
  const monthlyYears = new Set<string>();
  const monthsByYear = new Map<string, Set<string>>();
  const financialYears = new Set<string>();

  const tables = asRecord(client.tables);

  Object.entries(tables).forEach(([tableName, tablePayload]) => {
    const dedupedRows = dedupeRows(tableName, asArray(asRecord(tablePayload).rows));

    dedupedRows.forEach((row) => {
      if (!isUsableRow(row)) return;

      const meta = getRowMeta(tableName, row);
      registerAvailability(monthlyYears, monthsByYear, financialYears, meta);

      switch (tableName) {
        case 'gstr1_advance_tax':
          normalizeGstr1AdvanceTaxRows(datasets, row, meta);
          break;
        case 'gstr1_b2b':
          pushRowsFromRecords(datasets, 'gstr1_b2b', row.invoices, meta, (record) => ({
            ...record,
            rate: record.rate ?? record.tax_rate ?? '',
          }));
          break;
        case 'gstr1_summary':
          pushRowsFromRecords(datasets, 'gstr1_summary', row.sections, meta);
          break;
        case 'gstr1_b2csa':
        case 'gstr1_b2cs':
          pushRowsFromRecords(datasets, tableName, row.records, meta, normalizeGstr1B2csRecord);
          break;
        case 'gstr1_doc_issue':
        case 'gstr1_hsn':
        case 'gstr1_nil':
          pushRowsFromRecords(datasets, tableName, row.records, meta);
          break;
        case 'gstr1_b2cl':
        case 'gstr1_cdnr':
        case 'gstr1_cdnur':
        case 'gstr1_exp':
          pushRowsFromRecords(datasets, tableName, row.records, meta, normalizeGstr1ItemizedRecord);
          break;
        case 'gstr1_txp':
          normalizeGstr1TxpRows(datasets, row, meta);
          break;
        case 'gstr2a_b2b':
        case 'gstr2a_b2ba':
        case 'gstr2a_cdn':
        case 'gstr2a_cdna':
          pushRowsFromRecords(datasets, tableName, row.records, meta, normalizeGstr2aItemizedRecord);
          break;
        case 'gstr2a_document':
          normalizeGstr2aDocumentRows(datasets, row, meta);
          break;
        case 'gstr2a_isd':
          pushRowsFromRecords(datasets, 'gstr2a_isd', row.records, meta, (record) => ({
            ...record,
            isd_gstin: record.isd_gstin || record.distributor_gstin || '',
            itc_available: record.itc_available ?? record.itc_eligible ?? '',
          }));
          break;
        case 'gstr2a_tds':
          normalizeGstr2aTdsRows(datasets, row, meta);
          break;
        case 'gstr2b':
          pushDatasetRow(datasets, 'gstr2b_summary', {
            response_type: row.response_type,
            return_period: row.return_period,
            gen_date: row.gen_date,
            version: row.version,
            checksum: row.checksum,
            file_count: row.file_count,
            pagination_required: !!row.pagination_required,
            counterparty_summary: row.counterparty_summary,
            itc_summary: row.itc_summary,
            grand_summary: row.grand_summary,
          }, meta);
          normalizeGstr2bDocumentRows(datasets, row, meta);
          break;
        case 'gstr2b_regen_status':
          pushDatasetRow(datasets, 'gstr2b_regen_status', row, meta);
          break;
        case 'gstr3b_details':
          pushDatasetRow(datasets, 'gstr3b_details', row, meta);
          break;
        case 'gstr3b_auto_liability':
          pushDatasetRow(datasets, 'gstr3b_auto_liability', row, meta);
          break;
        case 'gstr9_auto_calculated':
          pushDatasetRow(datasets, 'gstr9_auto', row, meta);
          break;
        case 'gstr9_table8a':
          normalizeSupplierDocumentRows(datasets, 'gstr9_table8a', row.b2b, 'B2B', meta);
          normalizeSupplierDocumentRows(datasets, 'gstr9_table8a', row.b2ba, 'B2BA', meta);
          normalizeSupplierDocumentRows(datasets, 'gstr9_table8a', row.cdn, 'CDN', meta);
          break;
        case 'gstr9_details':
          pushDatasetRow(datasets, 'gstr9_details', {
            ...row,
            detail_sections: parseMaybeJsonObject(row.detail_sections),
          }, meta);
          break;
        case 'ledger_balance':
          pushDatasetRow(datasets, 'ledger_cash_balance', {
            ...row,
            cash_balance: {
              igst: {
                tax: toNumber(row.cash_igst_tax),
                interest: toNumber(row.cash_igst_interest),
                penalty: toNumber(row.cash_igst_penalty),
                fee: toNumber(row.cash_igst_fee),
                other: toNumber(row.cash_igst_other),
                total: toNumber(row.cash_igst_total),
              },
              cgst: { total: toNumber(row.cash_cgst_total) },
              sgst: { total: toNumber(row.cash_sgst_total) },
              cess: { total: toNumber(row.cash_cess_total) },
            },
            itc_balance: {
              igst: toNumber(row.itc_igst),
              cgst: toNumber(row.itc_cgst),
              sgst: toNumber(row.itc_sgst),
              cess: toNumber(row.itc_cess),
            },
            itc_blocked_balance: {
              igst: toNumber(row.itc_blocked_igst),
              cgst: toNumber(row.itc_blocked_cgst),
              sgst: toNumber(row.itc_blocked_sgst),
              cess: toNumber(row.itc_blocked_cess),
            },
          }, meta);
          break;
        case 'ledger_cash':
          asArray(row.transactions).forEach((transactionValue) => {
            const transaction = asRecord(transactionValue);
            const amount = asRecord(transaction.transaction_amount);
            pushDatasetRow(datasets, 'ledger_cash_txn', {
              ...transaction,
              ref_no: transaction.ref_no ?? transaction.reference_number ?? '',
              dt: transaction.dt ?? transaction.date ?? '',
              ret_period: transaction.ret_period ?? transaction.return_period ?? '',
              desc: transaction.desc ?? transaction.description ?? '',
              tr_typ: transaction.tr_typ ?? transaction.transaction_type ?? '',
              amount: toNumber(transaction.amount ?? amount.total),
            }, meta);
          });
          break;
        case 'ledger_itc':
          asArray(row.transactions).forEach((transactionValue) => {
            const transaction = asRecord(transactionValue);
            const amount = asRecord(transaction.transaction_amount);
            pushDatasetRow(datasets, 'ledger_itc_txn', {
              ...transaction,
              ref_no: transaction.ref_no ?? transaction.reference_number ?? '',
              dt: transaction.dt ?? transaction.date ?? '',
              ret_period: transaction.ret_period ?? transaction.return_period ?? '',
              desc: transaction.desc ?? transaction.description ?? '',
              tr_typ: transaction.tr_typ ?? transaction.transaction_type ?? '',
              amount: toNumber(transaction.amount ?? amount.total),
            }, meta);
          });
          break;
        case 'ledger_liability':
          asArray(row.transactions).forEach((transactionValue) => {
            const transaction = asRecord(transactionValue);
            pushDatasetRow(datasets, 'ledger_liability_txn', {
              ...transaction,
              ref_no: transaction.ref_no ?? transaction.reference_number ?? '',
              dt: transaction.dt ?? transaction.date ?? '',
              desc: transaction.desc ?? transaction.description ?? '',
              tr_typ: transaction.tr_typ ?? transaction.transaction_type ?? '',
              dschrg_typ: transaction.dschrg_typ ?? transaction.discharge_type ?? '',
              tot_tr_amt: toNumber(transaction.tot_tr_amt ?? transaction.total_transaction_amount),
            }, meta);
          });
          break;
        case 'gst_return_status':
          pushDatasetRow(datasets, 'gst_return_status', row, meta);
          break;
        default:
          if (!datasets[tableName]) datasets[tableName] = [];
      }
    });
  });

  const availability = finalizeAvailability(monthlyYears, monthsByYear, financialYears);
  const aliases: Record<string, any[]> = {
    gstr9_auto_calculated: datasets.gstr9_auto || [],
    ledger_balance: datasets.ledger_cash_balance || [],
    gstr1_at: datasets.gstr1_at || [],
  };

  return {
    datasets: {
      ...datasets,
      ...aliases,
    },
    availability,
    fetchedAt: new Date().toISOString(),
  };
}

export function buildClientDbSnapshot(payload: ProxyFetchPayload, gstin?: string): ClientDbSnapshot {
  const clients = asArray<ProxyClientPayload>(payload?.clients);
  const client = clients.find((item) => toText(item.gstin).toUpperCase() === toText(gstin).toUpperCase()) || clients[0];

  if (!client) {
    return {
      datasets: {},
      availability: EMPTY_AVAILABILITY,
      fetchedAt: new Date().toISOString(),
    };
  }

  return normalizeDashboardDatasets(client);
}

export function buildClientList(payload: unknown): DbProxyClient[] {
  return asArray<ProxyClientPayload>(payload)
    .map((client) => {
      const gstin = toText(client.gstin).toUpperCase();
      if (!gstin) return null;
      return {
        gstin,
        username: toText(client.username),
        label: toText(client.trade_name) || toText(client.legal_name) || gstin,
      };
    })
    .filter((client): client is DbProxyClient => client !== null);
}
