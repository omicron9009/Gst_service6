import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';

const cashColumns = [
  { key: 'head', label: 'Head' },
  { key: 'tax', label: 'Tax', type: 'currency' },
  { key: 'interest', label: 'Interest', type: 'currency' },
  { key: 'penalty', label: 'Penalty', type: 'currency' },
  { key: 'fee', label: 'Fee', type: 'currency' },
  { key: 'other', label: 'Other', type: 'currency' },
  { key: 'total', label: 'Total', type: 'currency' },
];

const itcColumns = [
  { key: 'head', label: 'Head' },
  { key: 'value', label: 'Value', type: 'currency' },
];

const itcTxnColumns = [
  { key: 'ref_no', label: 'Ref No' },
  { key: 'dt', label: 'Date' },
  { key: 'ret_period', label: 'Return Period' },
  { key: 'desc', label: 'Description' },
  { key: 'tr_typ', label: 'Type' },
  { key: 'igst_amt', label: 'IGST Amt', type: 'currency' },
  { key: 'cgst_amt', label: 'CGST Amt', type: 'currency' },
  { key: 'sgst_amt', label: 'SGST Amt', type: 'currency' },
  { key: 'cess_amt', label: 'Cess Amt', type: 'currency' },
  { key: 'total_amount', label: 'Total Amt', type: 'currency' },
  { key: 'igst_bal', label: 'IGST Bal', type: 'currency' },
  { key: 'cgst_bal', label: 'CGST Bal', type: 'currency' },
  { key: 'sgst_bal', label: 'SGST Bal', type: 'currency' },
  { key: 'cess_bal', label: 'Cess Bal', type: 'currency' },
  { key: 'total_range_balance', label: 'Range Balance', type: 'currency' },
];

const liabilityColumns = [
  { key: 'ref_no', label: 'Ref No' },
  { key: 'dt', label: 'Date' },
  { key: 'desc', label: 'Description' },
  { key: 'tr_typ', label: 'Type' },
  { key: 'dschrg_typ', label: 'Discharge' },
  { key: 'igst_amt', label: 'IGST Amt', type: 'currency' },
  { key: 'cgst_amt', label: 'CGST Amt', type: 'currency' },
  { key: 'sgst_amt', label: 'SGST Amt', type: 'currency' },
  { key: 'cess_amt', label: 'Cess Amt', type: 'currency' },
  { key: 'tot_tr_amt', label: 'Total Amt', type: 'currency' },
  { key: 'igst_bal', label: 'IGST Bal', type: 'currency' },
  { key: 'cgst_bal', label: 'CGST Bal', type: 'currency' },
  { key: 'sgst_bal', label: 'SGST Bal', type: 'currency' },
  { key: 'cess_bal', label: 'Cess Bal', type: 'currency' },
  { key: 'total_range_balance', label: 'Range Balance', type: 'currency' },
];

const buildCashRows = (cash: any) => {
  if (!cash) return [];
  return ['igst', 'cgst', 'sgst', 'cess'].map(head => ({
    head: head.toUpperCase(),
    tax: cash[head]?.tax,
    interest: cash[head]?.interest,
    penalty: cash[head]?.penalty,
    fee: cash[head]?.fee,
    other: cash[head]?.other,
    total: cash[head]?.total,
  }));
};

const buildItcRows = (itc: any) => {
  if (!itc) return [];
  return ['igst', 'cgst', 'sgst', 'cess'].map(head => ({ head: head.toUpperCase(), value: itc[head] }));
};

const normalizeBalanceRow = (row: any) => {
  if (row.cash_balance) return row;

  return {
    ...row,
    cash_balance: {
      igst: { tax: row.cash_igst_tax, interest: row.cash_igst_interest, penalty: row.cash_igst_penalty, fee: row.cash_igst_fee, other: row.cash_igst_other, total: row.cash_igst_total },
      cgst: { total: row.cash_cgst_total },
      sgst: { total: row.cash_sgst_total },
      cess: { total: row.cash_cess_total },
    },
    itc_balance: row.itc_balance || {
      igst: row.itc_igst,
      cgst: row.itc_cgst,
      sgst: row.itc_sgst,
      cess: row.itc_cess,
    },
    itc_blocked_balance: row.itc_blocked_balance || {
      igst: row.itc_blocked_igst,
      cgst: row.itc_blocked_cgst,
      sgst: row.itc_blocked_sgst,
      cess: row.itc_blocked_cess,
    },
  };
};

export function LedgerSections() {
  const { getData, loading } = useDbProxy();

  const cashBalance = getData('ledger_balance');
  const cashTxn = getData('ledger_cash');
  const liabilityTxn = getData('ledger_liability');

  const itcTransactions = Array.isArray(getData('ledger_itc')) ? getData('ledger_itc') : [];
  const liabilityTransactions = Array.isArray(liabilityTxn) ? liabilityTxn : [];

  return (
    <>
      <DashboardSection id="ledger-balance" title="Ledger — Cash + ITC Balance" loading={loading}>
        {cashBalance.length === 0 ? <EmptyState /> : (
          <div className="space-y-4">
            {cashBalance.map((row: any, i: number) => {
              const d = normalizeBalanceRow(row);
              return (
              <div key={i} className="space-y-4">
                {d.cash_balance && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground">Cash Balance</h4>
                    <DataTable columns={cashColumns} data={buildCashRows(d.cash_balance)} pageSize={10} />
                    <MetricGrid>
                      {['igst', 'cgst', 'sgst', 'cess'].map(head => (
                        <MetricCard key={head} label={`${head.toUpperCase()} Total`} value={d.cash_balance?.[head]?.total} isCurrency />
                      ))}
                    </MetricGrid>
                  </div>
                )}
                {d.itc_balance && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground">ITC Balance</h4>
                    <DataTable columns={itcColumns} data={buildItcRows(d.itc_balance)} pageSize={10} />
                  </div>
                )}
                {d.itc_blocked_balance && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground">ITC Blocked Balance</h4>
                    <DataTable columns={itcColumns} data={buildItcRows(d.itc_blocked_balance)} pageSize={10} />
                  </div>
                )}
              </div>
              );
            })}
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
        {itcTransactions.length === 0 ? <EmptyState /> : (
          <DataTable columns={itcTxnColumns} data={itcTransactions} pageSize={25} />
        )}
      </DashboardSection>

      <DashboardSection id="ledger-liability" title="Ledger — Return Liability" loading={loading}>
        {liabilityTransactions.length === 0 ? <EmptyState /> : (
          <DataTable columns={liabilityColumns} data={liabilityTransactions} pageSize={25} />
        )}
      </DashboardSection>
    </>
  );
}
