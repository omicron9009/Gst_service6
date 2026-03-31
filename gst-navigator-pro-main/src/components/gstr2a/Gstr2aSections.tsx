import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { detectColumnTypes } from '@/lib/column-utils';

export function Gstr2aSections() {
  const { getData, loading } = useDbProxy();

  const b2b = getData('gstr2a_b2b');
  const b2ba = getData('gstr2a_b2ba');
  const cdn = getData('gstr2a_cdn');
  const cdna = getData('gstr2a_cdna');
  const doc = getData('gstr2a_document');
  const isd = getData('gstr2a_isd');
  const tds = getData('gstr2a_tds');

  return (
    <>
      <DashboardSection id="gstr2a-b2b" title="GSTR-2A B2B / B2BA" loading={loading}>
        {b2b.length === 0 && b2ba.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'supplier_gstin', label: 'Supplier GSTIN', width: '160px' },
              { key: 'filing_status_gstr1', label: 'Filing Status' },
              { key: 'invoice_number', label: 'Invoice No' },
              { key: 'invoice_date', label: 'Invoice Date' },
              { key: 'invoice_type', label: 'Type' },
              { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
              { key: 'place_of_supply', label: 'POS' },
              { key: 'reverse_charge', label: 'RC' },
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

      <DashboardSection id="gstr2a-cdn" title="GSTR-2A CDN / CDNA" loading={loading}>
        {cdn.length === 0 && cdna.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'supplier_gstin', label: 'Supplier GSTIN' },
              { key: 'note_number', label: 'Note No' },
              { key: 'note_date', label: 'Note Date' },
              { key: 'note_type', label: 'Note Type' },
              { key: 'note_value', label: 'Note Value', type: 'currency' },
              { key: 'place_of_supply', label: 'POS' },
              { key: 'delete_flag', label: 'Del Flag' },
              { key: 'source_type', label: 'Source' },
              { key: 'irn', label: 'IRN' },
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

      <DashboardSection id="gstr2a-doc" title="GSTR-2A Documents (Aggregate)" loading={loading}>
        {doc.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={detectColumnTypes(doc)}
            data={doc}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr2a-isd" title="GSTR-2A ISD" loading={loading}>
        {isd.length === 0 ? <EmptyState /> : (
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

      <DashboardSection id="gstr2a-tds" title="GSTR-2A TDS" loading={loading}>
        {tds.length === 0 ? <EmptyState /> : (
          <>
            <MetricGrid>
              <MetricCard label="Total Deduction Base" value={tds.reduce((s: number, r: any) => {
                const val = r?.deduction_base_amount;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
              <MetricCard label="Total IGST" value={tds.reduce((s: number, r: any) => {
                const val = r?.igst;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
              <MetricCard label="Total CGST" value={tds.reduce((s: number, r: any) => {
                const val = r?.cgst;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
              <MetricCard label="Total SGST" value={tds.reduce((s: number, r: any) => {
                const val = r?.sgst;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
            </MetricGrid>
            <div className="mt-3">
              <DataTable
                columns={detectColumnTypes(tds)}
                data={tds}
              />
            </div>
          </>
        )}
      </DashboardSection>
    </>
  );
}
