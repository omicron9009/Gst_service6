import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { StructuredDataView } from '@/components/dashboard/StructuredDataView';

export function Gstr9Sections() {
  const { getData, getLastUpdated, loading } = useDbProxy();

  const auto = getData('gstr9_auto');
  const table8a = getData('gstr9_table8a');
  const details = getData('gstr9_details');

  return (
    <>
      <DashboardSection
        id="gstr9-auto"
        title="GSTR-9 Annual Return (Auto-Calculated)"
        loading={loading}
        lastUpdated={getLastUpdated('gstr9_auto')}
      >
        {auto.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4">
            {auto.map((item: any, index: number) => (
              <div key={index} className="space-y-4 rounded-xl border bg-card p-4">
                <MetricGrid>
                  <MetricCard label="Financial Period" value={item.financial_period || item.financial_year || '-'} />
                  <MetricCard label="Aggregate Turnover" value={item.aggregate_turnover} isCurrency />
                  <MetricCard label="HSN Min Length" value={item.hsn_min_length || '-'} />
                </MetricGrid>
                <StructuredDataView value={item.table4_outward_supplies} title="Table 4 Outward Supplies" />
                <StructuredDataView value={item.table5_exempt_nil_non_gst} title="Table 5 Exempt / Nil / Non-GST" />
                <StructuredDataView value={item.table6_itc_availed} title="Table 6 ITC Availed" />
                <StructuredDataView value={item.table8_itc_as_per_2b} title="Table 8 ITC As Per 2B" />
                <StructuredDataView value={item.table9_tax_paid} title="Table 9 Tax Paid" />
              </div>
            ))}
          </div>
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr9-8a"
        title="GSTR-9 Table 8A (ITC from Suppliers)"
        loading={loading}
        lastUpdated={getLastUpdated('gstr9_table8a')}
      >
        {table8a.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-full overflow-x-auto">
            <DataTable
              columns={[
                { key: 'document_section', label: 'Section' },
                { key: 'supplier_gstin', label: 'Supplier GSTIN', width: '160px' },
                { key: 'filing_date', label: 'Filing Date' },
                { key: 'return_period', label: 'Return Period' },
                { key: 'invoice_number', label: 'Invoice No' },
                { key: 'invoice_date', label: 'Invoice Date' },
                { key: 'invoice_value', label: 'Invoice Value', type: 'currency' },
                { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
                { key: 'igst', label: 'IGST', type: 'currency' },
                { key: 'cgst', label: 'CGST', type: 'currency' },
                { key: 'sgst', label: 'SGST', type: 'currency' },
                { key: 'cess', label: 'Cess', type: 'currency' },
              ]}
              data={table8a}
            />
          </div>
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr9-details"
        title="GSTR-9 Details (Full Return)"
        loading={loading}
        lastUpdated={getLastUpdated('gstr9_details')}
      >
        {details.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4">
            {details.map((item: any, index: number) => (
              <div key={index} className="rounded-xl border bg-card p-4 space-y-4">
                <StructuredDataView value={item.detail_sections || item} />
                <div>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Raw JSON
                  </div>
                  <div className="max-h-80 overflow-auto rounded-lg border bg-muted/20 p-3">
                    <pre className="text-xs leading-5 text-foreground whitespace-pre-wrap break-words">
                      {JSON.stringify(item.detail_sections || item, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </DashboardSection>
    </>
  );
}
