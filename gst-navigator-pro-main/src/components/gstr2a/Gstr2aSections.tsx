import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { formatCurrency } from '@/lib/formatters';

export function Gstr2aSections() {
  const { getData, getLastUpdated, loading } = useDbProxy();

  const b2b = getData('gstr2a_b2b');
  const b2ba = getData('gstr2a_b2ba');
  const cdn = getData('gstr2a_cdn');
  const cdna = getData('gstr2a_cdna');
  const doc = getData('gstr2a_document');
  const isd = getData('gstr2a_isd');
  const tds = getData('gstr2a_tds');

  return (
    <>
      <DashboardSection
        id="gstr2a-b2b"
        title="GSTR-2A B2B / B2BA"
        loading={loading}
        lastUpdated={getLastUpdated(['gstr2a_b2b', 'gstr2a_b2ba'])}
      >
        {b2b.length === 0 && b2ba.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'supplier_gstin', label: 'Supplier GSTIN', width: '160px' },
              { key: 'filing_status_gstr1', label: 'GSTR-1 Filing' },
              { key: 'invoice_number', label: 'Invoice No' },
              { key: 'invoice_date', label: 'Invoice Date' },
              { key: 'invoice_type', label: 'Type' },
              { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
              { key: 'place_of_supply', label: 'POS' },
              { key: 'reverse_charge', label: 'RC' },
              { key: 'tax_rate', label: 'Tax Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cgst', label: 'CGST', type: 'currency' },
              { key: 'sgst', label: 'SGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
            ]}
            data={[...b2b, ...b2ba]}
          />
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr2a-cdn"
        title="GSTR-2A CDN / CDNA"
        loading={loading}
        lastUpdated={getLastUpdated(['gstr2a_cdn', 'gstr2a_cdna'])}
      >
        {cdn.length === 0 && cdna.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'supplier_gstin', label: 'Supplier GSTIN', width: '160px' },
              { key: 'note_number', label: 'Note No' },
              { key: 'note_date', label: 'Note Date' },
              { key: 'note_type', label: 'Note Type' },
              { key: 'note_value', label: 'Note Value', type: 'currency' },
              { key: 'place_of_supply', label: 'POS' },
              { key: 'delete_flag', label: 'Delete Flag' },
              { key: 'source_type', label: 'Source Type' },
              { key: 'irn', label: 'IRN', width: '220px' },
              { key: 'tax_rate', label: 'Tax Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cgst', label: 'CGST', type: 'currency' },
              { key: 'sgst', label: 'SGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
            ]}
            data={[...cdn, ...cdna]}
          />
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr2a-doc"
        title="GSTR-2A Documents"
        loading={loading}
        lastUpdated={getLastUpdated('gstr2a_document')}
      >
        {doc.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-full overflow-x-auto">
            <DataTable
              columns={[
                { key: 'document_section', label: 'Section' },
                { key: 'supplier_gstin', label: 'Supplier GSTIN', width: '160px' },
                {
                  key: 'invoice_number',
                  label: 'Document No',
                  render: (_value, row) => row.invoice_number || row.note_number || '-',
                },
                {
                  key: 'invoice_date',
                  label: 'Document Date',
                  render: (_value, row) => row.invoice_date || row.note_date || '-',
                },
                {
                  key: 'invoice_type',
                  label: 'Document Type',
                  render: (_value, row) => row.invoice_type || row.note_type || '-',
                },
                {
                  key: 'invoice_value',
                  label: 'Document Value',
                  render: (_value, row) => formatCurrency(row.invoice_value ?? row.note_value ?? null),
                },
                { key: 'tax_rate', label: 'Tax Rate', type: 'number' },
                { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
                { key: 'igst', label: 'IGST', type: 'currency' },
                { key: 'cgst', label: 'CGST', type: 'currency' },
                { key: 'sgst', label: 'SGST', type: 'currency' },
                { key: 'cess', label: 'Cess', type: 'currency' },
              ]}
              data={doc}
            />
          </div>
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr2a-isd"
        title="GSTR-2A ISD"
        loading={loading}
        lastUpdated={getLastUpdated('gstr2a_isd')}
      >
        {isd.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'isd_gstin', label: 'ISD GSTIN' },
              { key: 'document_number', label: 'Document No' },
              { key: 'document_date', label: 'Document Date' },
              { key: 'document_type', label: 'Document Type' },
              { key: 'itc_available', label: 'ITC Available' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cgst', label: 'CGST', type: 'currency' },
              { key: 'sgst', label: 'SGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
            ]}
            data={isd}
          />
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr2a-tds"
        title="GSTR-2A TDS"
        loading={loading}
        lastUpdated={getLastUpdated('gstr2a_tds')}
      >
        {tds.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <MetricGrid>
              <MetricCard
                label="Deduction Base"
                value={tds.reduce((sum: number, row: any) => sum + (row.deduction_base_amount || 0), 0)}
                isCurrency
              />
              <MetricCard label="Total IGST" value={tds.reduce((sum: number, row: any) => sum + (row.igst || 0), 0)} isCurrency />
              <MetricCard label="Total CGST" value={tds.reduce((sum: number, row: any) => sum + (row.cgst || 0), 0)} isCurrency />
              <MetricCard label="Total SGST" value={tds.reduce((sum: number, row: any) => sum + (row.sgst || 0), 0)} isCurrency />
            </MetricGrid>
            <div className="mt-3">
              <DataTable
                columns={[
                  { key: 'deductor_gstin', label: 'Deductor GSTIN' },
                  { key: 'trade_name', label: 'Trade Name', width: '180px' },
                  { key: 'return_period', label: 'Return Period' },
                  { key: 'document_number', label: 'Document No' },
                  { key: 'document_date', label: 'Document Date' },
                  { key: 'deduction_base_amount', label: 'Deduction Base', type: 'currency' },
                  { key: 'igst', label: 'IGST', type: 'currency' },
                  { key: 'cgst', label: 'CGST', type: 'currency' },
                  { key: 'sgst', label: 'SGST', type: 'currency' },
                  { key: 'total_tds_credit', label: 'Total TDS Credit', type: 'currency' },
                ]}
                data={tds}
              />
            </div>
          </>
        )}
      </DashboardSection>
    </>
  );
}
