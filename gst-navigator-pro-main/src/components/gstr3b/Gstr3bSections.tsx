import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';

function renderObjectAsCards(obj: any, prefix = '') {
  if (!obj || typeof obj !== 'object') return null;
  return (
    <MetricGrid>
      {Object.entries(obj).map(([k, v]) => {
        if (typeof v === 'object' && v !== null) {
          return Object.entries(v as Record<string, any>).map(([k2, v2]) => (
            <MetricCard key={`${prefix}${k}-${k2}`} label={`${k.replace(/_/g, ' ')} — ${k2.replace(/_/g, ' ')}`} value={v2 as number} isCurrency={typeof v2 === 'number'} />
          ));
        }
        return <MetricCard key={`${prefix}${k}`} label={k.replace(/_/g, ' ')} value={v as any} isCurrency={typeof v === 'number'} />;
      }).flat()}
    </MetricGrid>
  );
}

export function Gstr3bSections() {
  const { getData, loading } = useDbProxy();

  const details = getData('gstr3b_details');
  const autoLiability = getData('gstr3b_auto_liability');

  return (
    <>
      <DashboardSection id="gstr3b-details" title="GSTR-3B Details" loading={loading}>
        {details.length === 0 ? <EmptyState /> : (
          <div className="space-y-6">
            {details.map((d: any, i: number) => (
              <div key={i} className="space-y-4">
                {d.supply_details && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Supply Details</h4>
                    {renderObjectAsCards(d.supply_details, 'supply-')}
                  </div>
                )}
                {d.inter_state_supplies && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Inter-State Supplies</h4>
                    {renderObjectAsCards(d.inter_state_supplies, 'inter-')}
                  </div>
                )}
                {d.eligible_itc && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Eligible ITC</h4>
                    {d.eligible_itc.itc_available && Array.isArray(d.eligible_itc.itc_available) && (
                      <DataTable
                        columns={Object.keys(d.eligible_itc.itc_available[0] || {}).map(k => ({
                          key: k, label: k.replace(/_/g, ' '),
                          type: typeof d.eligible_itc.itc_available[0]?.[k] === 'number' ? 'currency' as const : undefined
                        }))}
                        data={d.eligible_itc.itc_available}
                      />
                    )}
                    {d.eligible_itc.itc_net && renderObjectAsCards({ 'Net ITC': d.eligible_itc.itc_net }, 'net-')}
                  </div>
                )}
                {d.interest_and_late_fee && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Interest & Late Fee</h4>
                    {renderObjectAsCards(d.interest_and_late_fee, 'fee-')}
                  </div>
                )}
                {d.tax_payment && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Tax Payment</h4>
                    {renderObjectAsCards(d.tax_payment, 'tax-')}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>

      <DashboardSection id="gstr3b-auto" title="GSTR-3B Auto Liability" loading={loading}>
        {autoLiability.length === 0 ? <EmptyState /> : (
          <div className="space-y-3">
            {autoLiability.map((d: any, i: number) => (
              <div key={i}>
                {d.auto_calculated_liability && renderObjectAsCards(d.auto_calculated_liability, 'auto-')}
                {!d.auto_calculated_liability && (
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">{JSON.stringify(d, null, 2)}</pre>
                )}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>
    </>
  );
}
