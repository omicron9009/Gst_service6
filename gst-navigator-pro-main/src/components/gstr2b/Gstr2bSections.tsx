import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { JsonDisplay } from '@/components/dashboard/JsonDisplay';
import { detectColumnTypes } from '@/lib/column-utils';

export function Gstr2bSections() {
  const { getData, loading } = useDbProxy();

  const summary = getData('gstr2b');
  const documents = getData('gstr2b');
  const regenStatus = getData('gstr2b_regen_status');

  return (
    <>
      <DashboardSection id="gstr2b-summary" title="GSTR-2B Summary" loading={loading}>
        {summary.length === 0 ? <EmptyState /> : (
          <div className="space-y-3">
            <MetricGrid>
              {summary.map((s: any, i: number) => (
                <MetricCard key={i} label={s.response_type || 'Summary'} value={s.gen_date || '—'} />
              ))}
            </MetricGrid>
            <DataTable
              columns={detectColumnTypes(summary)}
              data={summary}
            />
          </div>
        )}
      </DashboardSection>

      <DashboardSection id="gstr2b-docs" title="GSTR-2B Documents" loading={loading}>
        {documents.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={detectColumnTypes(documents)}
            data={documents}
          />
        )}
      </DashboardSection>

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
