import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';

export function LedgerSections() {
  const { getData, loading } = useDbProxy();

  const cashBalance = getData('ledger_balance');
  const cashTxn = getData('ledger_cash');
  const itcTxn = getData('ledger_itc');
  const liabilityTxn = getData('ledger_liability');

  return (
    <>
      <DashboardSection id="ledger-balance" title="Ledger — Cash + ITC Balance" loading={loading}>
        {cashBalance.length === 0 ? <EmptyState /> : (
          <div className="space-y-4">
            {cashBalance.map((d: any, i: number) => (
              <div key={i} className="space-y-4">
                {d.cash_balance && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Cash Balance</h4>
                    <MetricGrid>
                      {Object.entries(d.cash_balance).map(([head, vals]: [string, any]) => (
                        <MetricCard key={head} label={`${head.toUpperCase()} Total`} value={vals?.total} isCurrency />
                      ))}
                    </MetricGrid>
                  </div>
                )}
                {d.itc_balance && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">ITC Balance</h4>
                    <MetricGrid>
                      {Object.entries(d.itc_balance).map(([k, v]: [string, any]) => (
                        <MetricCard key={k} label={k.toUpperCase()} value={v} isCurrency />
                      ))}
                    </MetricGrid>
                  </div>
                )}
                {d.itc_blocked_balance && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">ITC Blocked Balance</h4>
                    <MetricGrid>
                      {Object.entries(d.itc_blocked_balance).map(([k, v]: [string, any]) => (
                        <MetricCard key={k} label={k.toUpperCase()} value={v} isCurrency />
                      ))}
                    </MetricGrid>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>

      <DashboardSection id="ledger-cash" title="Ledger — Cash Transactions" loading={loading}>
        {cashTxn.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'ref_no', label: 'Ref No' },
              { key: 'dt', label: 'Date' },
              { key: 'ret_period', label: 'Return Period' },
              { key: 'desc', label: 'Description' },
              { key: 'tr_typ', label: 'Txn Type' },
              { key: 'amount', label: 'Amount', type: 'currency' },
            ]}
            data={cashTxn}
          />
        )}
      </DashboardSection>

      <DashboardSection id="ledger-itc" title="Ledger — ITC Transactions" loading={loading}>
        {itcTxn.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'ref_no', label: 'Ref No' },
              { key: 'dt', label: 'Date' },
              { key: 'ret_period', label: 'Return Period' },
              { key: 'desc', label: 'Description' },
              { key: 'tr_typ', label: 'Txn Type' },
              { key: 'amount', label: 'Amount', type: 'currency' },
            ]}
            data={itcTxn}
          />
        )}
      </DashboardSection>

      <DashboardSection id="ledger-liability" title="Ledger — Return Liability" loading={loading}>
        {liabilityTxn.length === 0 ? <EmptyState /> : (
          <DataTable
            columns={[
              { key: 'ref_no', label: 'Ref No' },
              { key: 'dt', label: 'Date' },
              { key: 'desc', label: 'Description' },
              { key: 'tr_typ', label: 'Txn Type' },
              { key: 'dschrg_typ', label: 'Discharge Type' },
              { key: 'tot_tr_amt', label: 'Total Amount', type: 'currency' },
            ]}
            data={liabilityTxn}
          />
        )}
      </DashboardSection>
    </>
  );
}
