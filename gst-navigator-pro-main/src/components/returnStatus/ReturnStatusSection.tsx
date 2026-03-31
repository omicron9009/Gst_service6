import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { EmptyState } from '@/components/dashboard/EmptyState';

export function ReturnStatusSection() {
  const { getData, loading } = useDbProxy();
  const data = getData('gst_return_status');

  return (
    <DashboardSection id="return-status" title="GST Return Status" loading={loading}>
      {data.length === 0 ? <EmptyState /> : (
        <div className="space-y-3">
          {data.map((d: any, i: number) => (
            <div key={i} className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center gap-4 flex-wrap">
                <span className="text-sm"><strong>Form Type:</strong> {d.form_type_label || d.form_type || '—'}</span>
                <span className="text-sm"><strong>Action:</strong> {d.action || '—'}</span>
                <span className="text-sm"><strong>Status:</strong> {d.processing_status_label || d.processing_status || '—'}</span>
                <span className={`status-badge ${d.has_errors ? 'status-error' : 'status-active'}`}>
                  {d.has_errors ? 'Has Errors' : 'No Errors'}
                </span>
              </div>
              {d.has_errors && d.error_report && typeof d.error_report === 'object' && (
                <div className="mt-2">
                  <h5 className="text-xs font-semibold text-muted-foreground mb-1">Error Report</h5>
                  {Object.entries(d.error_report).map(([section, errors]) => (
                    <div key={section} className="mb-2">
                      <h6 className="text-xs font-medium text-destructive">{section.replace(/_/g, ' ')}</h6>
                      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(errors, null, 2)}</pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
