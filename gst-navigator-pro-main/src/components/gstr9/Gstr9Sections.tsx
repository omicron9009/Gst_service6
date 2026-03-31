import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { JsonDisplay } from '@/components/dashboard/JsonDisplay';
import { detectColumnTypes } from '@/lib/column-utils';

export function Gstr9Sections() {
  const { getData, loading } = useDbProxy();

  const auto = getData('gstr9_auto_calculated');
  const table8a = getData('gstr9_table8a');
  const details = getData('gstr9_details');

  return (
    <>
      <DashboardSection id="gstr9-auto" title="GSTR-9 Annual Return (Auto-Calculated)" loading={loading}>
        {auto.length === 0 ? <EmptyState /> : (
          <div className="space-y-4">
            {auto.map((d: any, i: number) => (
              <div key={i} className="space-y-4">
                <MetricGrid>
                  <MetricCard label="Financial Period" value={d.financial_period} />
                  <MetricCard label="Aggregate Turnover" value={d.aggregate_turnover} isCurrency />
                  <MetricCard label="HSN Min Length" value={d.hsn_min_length} />
                </MetricGrid>
                {['table4_outward_supplies', 'table5_exempt_nil_non_gst', 'table6_itc_availed', 'table8_itc_as_per_2b', 'table9_tax_paid'].map(key => {
                  const section = d[key];
                  if (!section) return null;

                  // If it's an array of objects, display as table
                  if (Array.isArray(section) && section.length > 0 && typeof section[0] === 'object') {
                    return (
                      <div key={key}>
                        <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">{key.replace(/_/g, ' ')}</h4>
                        <DataTable
                          columns={detectColumnTypes(section)}
                          data={section}
                        />
                      </div>
                    );
                  }

                  // If it's a flat object, display as metrics
                  if (typeof section === 'object' && !Array.isArray(section)) {
                    const isAllNumbers = Object.values(section).every(v => typeof v === 'number' || v == null);
                    if (isAllNumbers) {
                      return (
                        <div key={key}>
                          <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">{key.replace(/_/g, ' ')}</h4>
                          <MetricGrid>
                            {Object.entries(section).map(([k, v]) => (
                              <MetricCard
                                key={k}
                                label={k.replace(/_/g, ' ')}
                                value={v as any}
                                isCurrency={k.toLowerCase().includes('tax') || k.toLowerCase().includes('value')}
                              />
                            ))}
                          </MetricGrid>
                        </div>
                      );
                    }
                  }

                  // For complex/unknown structures, use JSON display
                  return (
                    <div key={key}>
                      <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">{key.replace(/_/g, ' ')}</h4>
                      <JsonDisplay data={section} collapsible={false} maxHeight="250px" />
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>

      <DashboardSection id="gstr9-8a" title="GSTR-9 Table 8A (ITC from Suppliers)" loading={loading}>
        {table8a.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={detectColumnTypes(table8a)}
            data={table8a}
          />
        )}
      </DashboardSection>

      <DashboardSection id="gstr9-details" title="GSTR-9 Details (Full Return)" loading={loading}>
        {details.length === 0 ? <EmptyState /> : (
          <div className="space-y-3">
            {details.map((d: any, i: number) => (
              <div key={i} className="space-y-3">
                {d.detail_sections && typeof d.detail_sections === 'object' ? (
                  Object.entries(d.detail_sections).map(([key, val]) => {
                    // If it's an array of objects, display as table
                    if (Array.isArray(val) && val.length > 0 && typeof val[0] === 'object') {
                      return (
                        <div key={key}>
                          <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">{key.replace(/_/g, ' ')}</h4>
                          <DataTable
                            columns={detectColumnTypes(val)}
                            data={val}
                          />
                        </div>
                      );
                    }
                    // Otherwise use JSON display
                    return (
                      <div key={key}>
                        <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1">{key.replace(/_/g, ' ')}</h4>
                        <JsonDisplay data={val} collapsible={false} maxHeight="250px" />
                      </div>
                    );
                  })
                ) : (
                  <JsonDisplay data={d} collapsible={false} maxHeight="250px" />
                )}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>
    </>
  );
}
