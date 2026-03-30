import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { StructuredDataView } from '@/components/dashboard/StructuredDataView';

export function ReturnStatusSection() {
  const { getData, getLastUpdated, loading } = useDbProxy();
  const data = getData('gst_return_status');

  return (
    <DashboardSection
      id="return-status"
      title="GST Return Status"
      loading={loading}
      lastUpdated={getLastUpdated('gst_return_status')}
    >
      {data.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {data.map((item: any, index: number) => (
            <div key={index} className="rounded-xl border bg-card p-4">
              <div className="flex flex-wrap items-center gap-4">
                <span className="text-sm"><strong>Form Type:</strong> {item.form_type_label || item.form_type || '-'}</span>
                <span className="text-sm"><strong>Action:</strong> {item.action || '-'}</span>
                <span className="text-sm"><strong>Status:</strong> {item.processing_status_label || item.processing_status || '-'}</span>
                <span className={`status-badge ${item.has_errors ? 'status-error' : 'status-active'}`}>
                  {item.has_errors ? 'Has Errors' : 'No Errors'}
                </span>
              </div>
              {item.has_errors && item.error_report && (
                <div className="mt-4">
                  <StructuredDataView value={item.error_report} title="Error Report" />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
