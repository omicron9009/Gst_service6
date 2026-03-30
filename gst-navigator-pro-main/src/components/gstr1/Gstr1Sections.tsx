import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';

export function Gstr1Sections() {
  const { getData, getLastUpdated, loading } = useDbProxy();

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
  const at = getData('gstr1_at');
  const txp = getData('gstr1_txp');

  return (
    <>
      <DashboardSection
        id="gstr1-summary"
        title="GSTR-1 Summary"
        loading={loading}
        lastUpdated={getLastUpdated('gstr1_summary')}
      >
        {summary.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'sec_nm', label: 'Section Name' },
              { key: 'ttl_rec', label: 'Total Records', type: 'number' },
              { key: 'ttl_val', label: 'Total Value', type: 'currency' },
              { key: 'ttl_tax', label: 'Total Tax', type: 'currency' },
            ]}
            data={summary}
          />
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr1-b2b"
        title="GSTR-1 B2B (Business-to-Business)"
        loading={loading}
        lastUpdated={getLastUpdated('gstr1_b2b')}
      >
        {b2b.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <MetricGrid>
              <MetricCard label="Total Invoices" value={b2b.length} />
              <MetricCard label="Total Taxable Value" value={b2b.reduce((sum, row) => sum + (row.taxable_value || 0), 0)} isCurrency />
              <MetricCard label="Total IGST" value={b2b.reduce((sum, row) => sum + (row.igst || 0), 0)} isCurrency />
              <MetricCard label="Total CGST" value={b2b.reduce((sum, row) => sum + (row.cgst || 0), 0)} isCurrency />
              <MetricCard label="Total SGST" value={b2b.reduce((sum, row) => sum + (row.sgst || 0), 0)} isCurrency />
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

      <DashboardSection
        id="gstr1-b2cs"
        title="GSTR-1 B2CS / B2CSA"
        loading={loading}
        lastUpdated={getLastUpdated(['gstr1_b2cs', 'gstr1_b2csa'])}
      >
        {b2cs.length === 0 && b2csa.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'place_of_supply', label: 'Place of Supply' },
              { key: 'supply_type', label: 'Supply Type' },
              { key: 'invoice_type', label: 'Invoice Type' },
              { key: 'tax_rate', label: 'Tax Rate', type: 'number' },
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

      <DashboardSection
        id="gstr1-b2cl"
        title="GSTR-1 B2CL (Large)"
        loading={loading}
        lastUpdated={getLastUpdated('gstr1_b2cl')}
      >
        {b2cl.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'place_of_supply', label: 'Place of Supply' },
              { key: 'invoice_number', label: 'Invoice No' },
              { key: 'invoice_date', label: 'Invoice Date' },
              { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
              { key: 'tax_rate', label: 'Tax Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
              { key: 'flag', label: 'Flag' },
            ]}
            data={b2cl}
          />
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr1-cdn"
        title="GSTR-1 Credit/Debit Notes (CDNR / CDNUR)"
        loading={loading}
        lastUpdated={getLastUpdated(['gstr1_cdnr', 'gstr1_cdnur'])}
      >
        {cdnr.length === 0 && cdnur.length === 0 ? (
          <EmptyState />
        ) : (
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

      <DashboardSection
        id="gstr1-exp"
        title="GSTR-1 Exports (EXP)"
        loading={loading}
        lastUpdated={getLastUpdated('gstr1_exp')}
      >
        {exp.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'export_type', label: 'Export Type' },
              { key: 'invoice_number', label: 'Invoice No' },
              { key: 'invoice_date', label: 'Invoice Date' },
              { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
              { key: 'tax_rate', label: 'Tax Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cess', label: 'Cess', type: 'currency' },
            ]}
            data={exp}
          />
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr1-nil"
        title="GSTR-1 Nil Rated"
        loading={loading}
        lastUpdated={getLastUpdated('gstr1_nil')}
      >
        {nil.length === 0 ? (
          <EmptyState />
        ) : (
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

      <DashboardSection
        id="gstr1-hsn"
        title="GSTR-1 HSN Summary"
        loading={loading}
        lastUpdated={getLastUpdated('gstr1_hsn')}
      >
        {hsn.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={[
              { key: 'serial_number', label: 'Sr No' },
              { key: 'hsn_sac_code', label: 'HSN/SAC Code' },
              { key: 'description', label: 'Description', width: '220px' },
              { key: 'unit_of_quantity', label: 'UQC' },
              { key: 'quantity', label: 'Quantity', type: 'number' },
              { key: 'tax_rate', label: 'Tax Rate', type: 'number' },
              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
              { key: 'igst', label: 'IGST', type: 'currency' },
              { key: 'cgst', label: 'CGST', type: 'currency' },
              { key: 'sgst', label: 'SGST', type: 'currency' },
            ]}
            data={hsn}
          />
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr1-doc"
        title="GSTR-1 Document Issued"
        loading={loading}
        lastUpdated={getLastUpdated('gstr1_doc_issue')}
      >
        {docIssue.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-full overflow-x-auto">
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
          </div>
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr1-at-txp"
        title="GSTR-1 Advance Tax (AT) & TXP"
        loading={loading}
        lastUpdated={getLastUpdated(['gstr1_at', 'gstr1_txp'])}
      >
        {at.length === 0 && txp.length === 0 ? (
          <EmptyState />
        ) : (
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
                    { key: 'place_of_supply', label: 'Place of Supply' },
                    { key: 'supply_type', label: 'Supply Type' },
                    { key: 'rate', label: 'Rate', type: 'number' },
                    { key: 'advance_amount', label: 'Advance Amount', type: 'currency' },
                    { key: 'igst', label: 'IGST', type: 'currency' },
                    { key: 'cgst', label: 'CGST', type: 'currency' },
                    { key: 'sgst', label: 'SGST', type: 'currency' },
                    { key: 'cess', label: 'Cess', type: 'currency' },
                    { key: 'total_tax', label: 'Total Tax', type: 'currency' },
                    { key: 'flag', label: 'Flag' },
                    { key: 'action_required', label: 'Action Required' },
                  ]}
                  data={txp}
                />
              </>
            )}
          </div>
        )}
      </DashboardSection>
    </>
  );
}
