import { useMemo } from 'react';
import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { JsonDisplay } from '@/components/dashboard/JsonDisplay';
import { detectColumnTypes } from '@/lib/column-utils';
import { formatCurrency } from '@/lib/formatters';

const HIDDEN_COLS = new Set(['section', 'irn', 'irn_gen_date', 'diff_percent', 'reason', 'ims_status']);

function filterColumns(data: any[]) {
  const cols = detectColumnTypes(data);
  return cols.filter(c => !HIDDEN_COLS.has(c.key));
}

/* ── ITC Summary Table ─────────────────────────────────────────────────── */

interface TaxBlock {
  taxable_value: number;
  igst: number;
  cgst: number;
  sgst: number;
  cess: number;
}

const ZERO_BLOCK: TaxBlock = { taxable_value: 0, igst: 0, cgst: 0, sgst: 0, cess: 0 };

function tb(obj: any): TaxBlock {
  if (!obj || typeof obj !== 'object') return ZERO_BLOCK;
  return {
    taxable_value: obj.taxable_value ?? 0,
    igst: obj.igst ?? 0,
    cgst: obj.cgst ?? 0,
    sgst: obj.sgst ?? 0,
    cess: obj.cess ?? 0,
  };
}

function fmt(v: number) {
  return v === 0 ? '—' : formatCurrency(v);
}

function ItcSummaryTable({ data }: { data: any }) {
  const avail = data?.itc_available ?? {};
  const unavail = data?.itc_unavailable ?? {};

  const nonRev = avail.non_reverse_supply ?? {};
  const other = avail.other_supply ?? {};
  const rev = avail.reverse_supply ?? {};
  const unavailNonRev = unavail.non_reverse_supply ?? {};

  const rows: { label: string; indent?: boolean; bold?: boolean; block: TaxBlock }[] = [
    { label: 'ITC Available', bold: true, block: ZERO_BLOCK },
    { label: 'Non-Reverse Supply — B2B', indent: true, block: tb(nonRev.b2b) },
    { label: 'Non-Reverse Supply — B2BA', indent: true, block: tb(nonRev.b2ba) },
    { label: 'Non-Reverse Supply — CDNR', indent: true, block: tb(nonRev.cdnr) },
    { label: 'Non-Reverse Supply — Total', indent: true, bold: true, block: tb(nonRev.total) },
    { label: 'Other Supply — CDNR', indent: true, block: tb(other.cdnr) },
    { label: 'Other Supply — CDNR (Reverse)', indent: true, block: tb(other.cdnr_rev) },
    { label: 'Other Supply — Total', indent: true, bold: true, block: tb(other.total) },
    { label: 'Reverse Supply — B2B', indent: true, block: tb(rev.b2b) },
    { label: 'Reverse Supply — Total', indent: true, bold: true, block: tb(rev.total) },
    { label: 'ITC Unavailable', bold: true, block: ZERO_BLOCK },
    { label: 'Non-Reverse Supply — B2B', indent: true, block: tb(unavailNonRev.b2b) },
    { label: 'Non-Reverse Supply — Total', indent: true, bold: true, block: tb(unavailNonRev.total) },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="text-left py-2 px-3 font-semibold">Category</th>
            <th className="text-right py-2 px-3 font-semibold">Taxable Value</th>
            <th className="text-right py-2 px-3 font-semibold">IGST</th>
            <th className="text-right py-2 px-3 font-semibold">CGST</th>
            <th className="text-right py-2 px-3 font-semibold">SGST</th>
            <th className="text-right py-2 px-3 font-semibold">Cess</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const isHeader = row.bold && !row.indent;
            return (
              <tr
                key={i}
                className={`border-b ${isHeader ? 'bg-muted/30' : ''} ${row.bold ? 'font-semibold' : ''}`}
              >
                <td className={`py-2 px-3 ${row.indent ? 'pl-8' : ''}`}>{row.label}</td>
                {isHeader ? (
                  <td colSpan={5} />
                ) : (
                  <>
                    <td className="text-right py-2 px-3">{fmt(row.block.taxable_value)}</td>
                    <td className="text-right py-2 px-3">{fmt(row.block.igst)}</td>
                    <td className="text-right py-2 px-3">{fmt(row.block.cgst)}</td>
                    <td className="text-right py-2 px-3">{fmt(row.block.sgst)}</td>
                    <td className="text-right py-2 px-3">{fmt(row.block.cess)}</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────────────── */

export function Gstr2bSections() {
  const { getData, loading } = useDbProxy();

  const allRecords = getData('gstr2b');
  const regenStatus = getData('gstr2b_regen_status');

  const sections = useMemo(() => {
    const metadata = allRecords.filter((r: any) => r.section === 'metadata');
    const grandSummary = allRecords.filter((r: any) => r.section === 'grand_summary');
    const b2b = allRecords.filter((r: any) => r.section === 'b2b');
    const b2ba = allRecords.filter((r: any) => r.section === 'b2ba');
    const cdnr = allRecords.filter((r: any) => r.section === 'cdnr');
    const cdnra = allRecords.filter((r: any) => r.section === 'cdnra');
    const isd = allRecords.filter((r: any) => r.section === 'isd');
    const cpsummB2b = allRecords.filter((r: any) => r.section === 'cpsumm_b2b');
    const cpsummCdnr = allRecords.filter((r: any) => r.section === 'cpsumm_cdnr');
    const itcSummary = allRecords.filter((r: any) => r.section === 'itc_summary');
    return { metadata, grandSummary, b2b, b2ba, cdnr, cdnra, isd, cpsummB2b, cpsummCdnr, itcSummary };
  }, [allRecords]);

  const meta = sections.metadata[0];
  const grand = sections.grandSummary[0];

  if (allRecords.length === 0 && regenStatus.length === 0) {
    return (
      <DashboardSection id="gstr2b" title="GSTR-2B" loading={loading}>
        <EmptyState />
      </DashboardSection>
    );
  }

  return (
    <>
      {/* ── Overview ──────────────────────────────────────────────── */}
      <DashboardSection id="gstr2b-overview" title="GSTR-2B Overview" loading={loading}>
        {meta ? (
          <MetricGrid>
            <MetricCard label="Return Period" value={meta.return_period || '—'} />
            <MetricCard label="Generated Date" value={meta.gen_date || '—'} />
            <MetricCard label="GSTIN" value={meta.gstin || '—'} />
            <MetricCard label="Response Type" value={meta.response_type || '—'} />
            {grand && (
              <>
                <MetricCard label="B2B Invoices" value={grand.total_b2b_invoices ?? 0} />
                <MetricCard label="CDNR Notes" value={grand.total_cdnr_notes ?? 0} />
                <MetricCard label="Taxable Value" value={grand.taxable ?? 0} isCurrency />
                <MetricCard label="CGST" value={grand.cgst ?? 0} isCurrency />
                <MetricCard label="SGST" value={grand.sgst ?? 0} isCurrency />
                <MetricCard label="IGST" value={grand.igst ?? 0} isCurrency />
                <MetricCard label="Cess" value={grand.cess ?? 0} isCurrency />
                <MetricCard label="Total Invoice Value" value={grand.invoice_value ?? 0} isCurrency />
              </>
            )}
          </MetricGrid>
        ) : (
          <EmptyState />
        )}
      </DashboardSection>

      {/* ── B2B Invoices ──────────────────────────────────────────── */}
      <DashboardSection
        id="gstr2b-b2b"
        title={`B2B — Inward Supplies (${sections.b2b.length})`}
        loading={loading}
      >
        {sections.b2b.length === 0 ? <EmptyState /> : (
          <DataTable columns={filterColumns(sections.b2b)} data={sections.b2b} />
        )}
      </DashboardSection>

      {/* ── B2BA Amended ──────────────────────────────────────────── */}
      {sections.b2ba.length > 0 && (
        <DashboardSection
          id="gstr2b-b2ba"
          title={`B2BA — Amended Inward Supplies (${sections.b2ba.length})`}
          loading={loading}
        >
          <DataTable columns={filterColumns(sections.b2ba)} data={sections.b2ba} />
        </DashboardSection>
      )}

      {/* ── CDNR Credit/Debit Notes ──────────────────────────────── */}
      <DashboardSection
        id="gstr2b-cdnr"
        title={`CDNR — Credit/Debit Notes (${sections.cdnr.length})`}
        loading={loading}
      >
        {sections.cdnr.length === 0 ? <EmptyState /> : (
          <DataTable columns={filterColumns(sections.cdnr)} data={sections.cdnr} />
        )}
      </DashboardSection>

      {/* ── CDNRA Amended Notes ───────────────────────────────────── */}
      {sections.cdnra.length > 0 && (
        <DashboardSection
          id="gstr2b-cdnra"
          title={`CDNRA — Amended Credit/Debit Notes (${sections.cdnra.length})`}
          loading={loading}
        >
          <DataTable columns={filterColumns(sections.cdnra)} data={sections.cdnra} />
        </DashboardSection>
      )}

      {/* ── ISD Entries ───────────────────────────────────────────── */}
      {sections.isd.length > 0 && (
        <DashboardSection
          id="gstr2b-isd"
          title={`ISD — Input Service Distributor (${sections.isd.length})`}
          loading={loading}
        >
          <DataTable columns={filterColumns(sections.isd)} data={sections.isd} />
        </DashboardSection>
      )}

      {/* ── Counterparty Summary (shape A responses) ──────────────── */}
      {sections.cpsummB2b.length > 0 && (
        <DashboardSection
          id="gstr2b-cpsumm-b2b"
          title={`Counterparty Summary — B2B (${sections.cpsummB2b.length})`}
          loading={loading}
        >
          <DataTable columns={filterColumns(sections.cpsummB2b)} data={sections.cpsummB2b} />
        </DashboardSection>
      )}

      {sections.cpsummCdnr.length > 0 && (
        <DashboardSection
          id="gstr2b-cpsumm-cdnr"
          title={`Counterparty Summary — CDNR (${sections.cpsummCdnr.length})`}
          loading={loading}
        >
          <DataTable columns={filterColumns(sections.cpsummCdnr)} data={sections.cpsummCdnr} />
        </DashboardSection>
      )}

      {/* ── ITC Summary ───────────────────────────────────────────── */}
      {sections.itcSummary.length > 0 && (
        <DashboardSection id="gstr2b-itc" title="ITC Summary" loading={loading}>
          <ItcSummaryTable data={sections.itcSummary[0]} />
        </DashboardSection>
      )}

      {/* ── Regeneration Status ───────────────────────────────────── */}
      <DashboardSection id="gstr2b-regen" title="GSTR-2B Regeneration Status" loading={loading}>
        {regenStatus.length === 0 ? <EmptyState /> : (
          <div className="space-y-3">
            {regenStatus.map((s: any, i: number) => (
              <div key={i} className="rounded-lg border p-4 space-y-2">
                <div className="flex items-center gap-4 flex-wrap">
                  <span className="text-sm"><strong>Form Type:</strong> {s.form_type_label || '—'}</span>
                  <span className="text-sm"><strong>Action:</strong> {s.action || '—'}</span>
                  <span className="text-sm"><strong>Status:</strong> {s.processing_status_label || '—'}</span>
                  <span className={`status-badge ${s.has_errors ? 'status-error' : 'status-active'}`}>
                    {s.has_errors ? 'Has Errors' : 'No Errors'}
                  </span>
                </div>
                {s.error_report && typeof s.error_report === 'object' && Object.keys(s.error_report).length > 0 && (
                  <div className="mt-2">
                    <h5 className="text-xs font-semibold text-muted-foreground mb-1">Error Report</h5>
                    <JsonDisplay data={s.error_report} collapsible={false} maxHeight="200px" />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>
    </>
  );
}
