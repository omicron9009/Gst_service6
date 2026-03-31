import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Gstr1Summary } from './Gstr1Summary';

export function Gstr1Sections() {
  const { getData, loading } = useDbProxy();

  const summary = getData('gstr1_summary');
  const b2b = getData('gstr1_b2b');
  const b2cs = getData('gstr1_b2cs');
  const b2csa = getData('gstr1_b2csa');
  const b2cl = getData('gstr1_b2cl');
  const cdnr = getData('gstr1_cdnr');
  const cdnur = getData('gstr1_cdnur');
  const exp = getData('gstr1_exp');
  const nil = getData('gstr1_nil');
  const hsn = getData('gstr1_hsn');
  const docIssue = getData('gstr1_doc_issue');
  const at = getData('gstr1_advance_tax');
  const txp = getData('gstr1_txp');

  // Flatten TXP rows for display; pick first item rate/advance and use totals for sums.
  const txpRows = txp.map((row: any) => {
    const firstItem = (row.items && row.items[0]) || {};
    const totals = row.totals || {};
    return {
      pos: row.pos,
      flag: row.flag,
      supply_type: row.supply_type,
      action_required: row.action_required,
      tax_rate: firstItem.tax_rate,
      advance_amount: firstItem.advance_amount,
      cgst: totals.cgst,
      sgst: totals.sgst,
      igst: totals.igst,
      cess: totals.cess,
      total_tax: totals.total_tax,
      checksum: row.checksum,
    };
  });

  return (
    <>
      <DashboardSection id="gstr1-summary" title="GSTR-1 Summary" loading={loading}>
        <Gstr1Summary summary={summary} loading={loading} />
      </DashboardSection>

      <DashboardSection id="gstr1-b2b" title="GSTR-1 B2B (Business-to-Business)" loading={loading}>
        {b2b.length === 0 ? <EmptyState /> : (
          <>
            <MetricGrid>
              <MetricCard label="Total Invoices" value={b2b.length} />
              <MetricCard label="Total Taxable Value" value={b2b.reduce((s, r) => {
                const val = r?.taxable_value;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
              <MetricCard label="Total IGST" value={b2b.reduce((s, r) => {
                const val = r?.igst;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
              <MetricCard label="Total CGST" value={b2b.reduce((s, r) => {
                const val = r?.cgst;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
              <MetricCard label="Total SGST" value={b2b.reduce((s, r) => {
                const val = r?.sgst;
                return s + (typeof val === 'number' ? val : 0);
              }, 0)} isCurrency />
            </MetricGrid>
            <div className="mt-3">
              <DataTable
                columns={[
                  { key: 'counterparty_gstin', label: 'GSTIN', width: '160px' },
                  { key: 'invoice_number', label: 'Invoice No' },
                  { key: 'invoice_date', label: 'Invoice Date' },
                  { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
                  { key: 'rate', label: 'Rate', type: 'number' },
                  { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
                  { key: 'igst', label: 'IGST', type: 'currency' },
                  { key: 'cgst', label: 'CGST', type: 'currency' },
                  { key: 'sgst', label: 'SGST', type: 'currency' },
                  { key: 'cess', label: 'Cess', type: 'currency' },
                ]}
                data={b2b}
              />
            </div>
          </>
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-b2cs" title="GSTR-1 B2CS / B2CSA" loading={loading}>
        {b2cs.length === 0 && b2csa.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'place_of_supply', label: 'Place of Supply' },
              { key: 'supply_type', label: 'Supply Type' },
              { key: 'invoice_type', label: 'Invoice Type' },
              { key: 'rate', label: 'Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cgst', label: 'CGST', type: 'currency' },
              { key: 'sgst', label: 'SGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
              { key: 'flag', label: 'Flag' },
            ]}
            data={[...b2cs, ...b2csa]}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-b2cl" title="GSTR-1 B2CL (Large)" loading={loading}>
        {b2cl.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'place_of_supply', label: 'Place of Supply' },
              { key: 'invoice_number', label: 'Invoice No' },
              { key: 'invoice_date', label: 'Invoice Date' },
              { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
              { key: 'rate', label: 'Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
              { key: 'flag', label: 'Flag' },
            ]}
            data={b2cl}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-cdn" title="GSTR-1 Credit/Debit Notes (CDNR / CDNUR)" loading={loading}>
        {cdnr.length === 0 && cdnur.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'counterparty_gstin', label: 'GSTIN' },
              { key: 'note_number', label: 'Note No' },
              { key: 'note_date', label: 'Note Date' },
              { key: 'note_type', label: 'Note Type' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cgst', label: 'CGST', type: 'currency' },
              { key: 'sgst', label: 'SGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
            ]}
            data={[...cdnr, ...cdnur]}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-exp" title="GSTR-1 Exports (EXP)" loading={loading}>
        {exp.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'export_type', label: 'Export Type' },
              { key: 'invoice_number', label: 'Invoice No' },
              { key: 'invoice_date', label: 'Invoice Date' },
              { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
              { key: 'rate', label: 'Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
            ]}
            data={exp}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-nil" title="GSTR-1 Nil Rated" loading={loading}>
        {nil.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'supply_type', label: 'Supply Type' },
              { key: 'nil_rated_amount', label: 'Nil Rated Amount', type: 'currency' },
              { key: 'exempted_amount', label: 'Exempted Amount', type: 'currency' },
              { key: 'non_gst_amount', label: 'Non-GST Amount', type: 'currency' },
            ]}
            data={nil}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-hsn" title="GSTR-1 HSN Summary" loading={loading}>
        {hsn.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'serial_number', label: 'Sr No' },
              { key: 'hsn_sac_code', label: 'HSN/SAC Code' },
              { key: 'description', label: 'Description' },
              { key: 'unit_of_quantity', label: 'UQC' },
              { key: 'quantity', label: 'Quantity', type: 'number' },
              { key: 'rate', label: 'Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cgst', label: 'CGST', type: 'currency' },
              { key: 'sgst', label: 'SGST', type: 'currency' },
            ]}
            data={hsn}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-doc" title="GSTR-1 Document Issued" loading={loading}>
        {docIssue.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'document_type_number', label: 'Document Type' },
              { key: 'serial_number', label: 'Serial No' },
              { key: 'from_serial', label: 'From Serial' },
              { key: 'to_serial', label: 'To Serial' },
              { key: 'total_issued', label: 'Total Issued', type: 'number' },
              { key: 'cancelled', label: 'Cancelled', type: 'number' },
              { key: 'net_issued', label: 'Net Issued', type: 'number' },
            ]}
            data={docIssue}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr1-at-txp" title="GSTR-1 Advance Tax (AT) & TXP" loading={loading}>
        {at.length === 0 && txp.length === 0 ? <EmptyState /> : (
          <div className="space-y-4">
            {at.length > 0 && (
              <>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">Advance Tax</h4>
                <DataTable
                  columns={[
                    { key: 'place_of_supply', label: 'Place of Supply' },
                    { key: 'supply_type', label: 'Supply Type' },
                    { key: 'rate', label: 'Rate', type: 'number' },
                    { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
                    { key: 'igst', label: 'IGST', type: 'currency' },
                    { key: 'cgst', label: 'CGST', type: 'currency' },
                    { key: 'sgst', label: 'SGST', type: 'currency' },
                    { key: 'cess', label: 'Cess', type: 'currency' },
                  ]}
                  data={at}
                />
              </>
            )}
            {txp.length > 0 && (
              <>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">Tax Payment (TXP)</h4>
                <DataTable
                  columns={[
                    { key: 'pos', label: 'POS' },
                    { key: 'flag', label: 'Flag' },
                    { key: 'supply_type', label: 'Supply Type' },
                    { key: 'action_required', label: 'Action Required' },
                    { key: 'tax_rate', label: 'Rate', type: 'number' },
                    { key: 'advance_amount', label: 'Advance Amount', type: 'currency' },
                    { key: 'cgst', label: 'CGST', type: 'currency' },
                    { key: 'sgst', label: 'SGST', type: 'currency' },
                    { key: 'igst', label: 'IGST', type: 'currency' },
                    { key: 'cess', label: 'Cess', type: 'currency' },
                    { key: 'total_tax', label: 'Total Tax', type: 'currency' },
                    { key: 'checksum', label: 'Checksum', width: '240px' },
                  ]}
                  data={txpRows}
                />
              </>
            )}
          </div>
        )}
      </DashboardSection>
    </>
  );
}
