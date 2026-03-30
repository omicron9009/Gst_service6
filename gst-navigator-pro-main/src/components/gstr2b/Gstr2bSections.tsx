import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { StructuredDataView } from '@/components/dashboard/StructuredDataView';
import { formatCurrency } from '@/lib/formatters';

export function Gstr2bSections() {
  const { getData, getLastUpdated, loading } = useDbProxy();

  const summary = getData('gstr2b_summary');
  const documents = getData('gstr2b_documents');
  const regenStatus = getData('gstr2b_regen_status');

  return (
    <>
      <DashboardSection
        id="gstr2b-summary"
        title="GSTR-2B Summary"
        loading={loading}
        lastUpdated={getLastUpdated('gstr2b_summary')}
      >
        {summary.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4">
            {summary.map((item: any, index: number) => (
              <div key={index} className="space-y-4 rounded-xl border bg-card p-4">
                <MetricGrid>
                  <MetricCard label="Response Type" value={item.response_type || '-'} />
                  <MetricCard label="Return Period" value={item.return_period || '-'} />
                  <MetricCard label="Generated On" value={item.gen_date || '-'} />
                  <MetricCard label="Version" value={item.version || '-'} />
                  <MetricCard label="File Count" value={item.file_count ?? 0} />
                  <MetricCard label="Pagination Required" value={item.pagination_required ? 'Yes' : 'No'} />
                </MetricGrid>
                <StructuredDataView value={item.counterparty_summary} title="Counterparty Summary" />
                <StructuredDataView value={item.itc_summary} title="ITC Summary" />
                <StructuredDataView value={item.grand_summary} title="Grand Summary" />
              </div>
            ))}
          </div>
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr2b-docs"
        title="GSTR-2B Documents"
        loading={loading}
        lastUpdated={getLastUpdated('gstr2b_documents')}
      >
        {documents.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-full overflow-x-auto">
            <DataTable
              columns={[
                { key: 'document_section', label: 'Section' },
                { key: 'supplier_gstin', label: 'Supplier / ISD GSTIN', width: '160px' },
                {
                  key: 'invoice_number',
                  label: 'Document No',
                  render: (_value, row) => row.invoice_number || row.note_number || row.document_number || '-',
                },
                {
                  key: 'invoice_date',
                  label: 'Document Date',
                  render: (_value, row) => row.invoice_date || row.note_date || row.document_date || '-',
                },
                {
                  key: 'invoice_value',
                  label: 'Document Value',
                  render: (_value, row) => formatCurrency(row.invoice_value ?? row.note_value ?? null),
                },
                { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
                { key: 'igst', label: 'IGST', type: 'currency' },
                { key: 'cgst', label: 'CGST', type: 'currency' },
                { key: 'sgst', label: 'SGST', type: 'currency' },
                { key: 'cess', label: 'Cess', type: 'currency' },
                { key: 'total_tax', label: 'Total Tax', type: 'currency' },
              ]}
              data={documents}
            />
          </div>
        )}
      </DashboardSection>

      <DashboardSection
        id="gstr2b-regen"
        title="GSTR-2B Regeneration Status"
        loading={loading}
        lastUpdated={getLastUpdated('gstr2b_regen_status')}
      >
        {regenStatus.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            {regenStatus.map((item: any, index: number) => (
              <div key={index} className="rounded-xl border bg-card p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm"><strong>Form Type:</strong> {item.form_type_label || '-'}</span>
                  <span className="text-sm"><strong>Action:</strong> {item.action || '-'}</span>
                  <span className="text-sm"><strong>Status:</strong> {item.processing_status_label || '-'}</span>
                  <span className={`status-badge ${item.has_errors ? 'status-error' : 'status-active'}`}>
                    {item.has_errors ? 'Has Errors' : 'No Errors'}
                  </span>
                </div>
                {item.error_report && (
                  <div className="mt-4">
                    <StructuredDataView value={item.error_report} title="Error Report" />
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
