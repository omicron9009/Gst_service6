import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';

const renderTaxBlock = (title: string, block: any) => {
  if (!block) return null;
  return (
    <div>
      <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1">{title}</h5>
      <MetricGrid>
        <MetricCard label="Taxable Value" value={block.taxable_value} isCurrency />
        <MetricCard label="IGST" value={block.igst} isCurrency />
        <MetricCard label="CGST" value={block.cgst} isCurrency />
        <MetricCard label="SGST" value={block.sgst} isCurrency />
        <MetricCard label="Cess" value={block.cess} isCurrency />
      </MetricGrid>
    </div>
  );
};

const formatLabel = (text: string) => text.replace(/_/g, ' ');

const taxColumns = [
  { key: 'label', label: 'Type' },
  { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
  { key: 'igst', label: 'IGST', type: 'currency' },
  { key: 'cgst', label: 'CGST', type: 'currency' },
  { key: 'sgst', label: 'SGST', type: 'currency' },
  { key: 'cess', label: 'Cess', type: 'currency' },
];

const renderItcSection = (title: string, section: any) => {
  if (!section) return null;
  const rows = ['itc_available', 'itc_available_cn', 'itc_unavailable'].map(key => ({
    label: formatLabel(key),
    ...(section[key] || {}),
  }));

  return (
    <div className="space-y-2">
      <h5 className="text-[11px] font-semibold uppercase text-muted-foreground">{title}</h5>
      {section.subtotal && (
        <MetricGrid>
          <MetricCard label="Taxable Value" value={section.subtotal.taxable_value} isCurrency />
          <MetricCard label="IGST" value={section.subtotal.igst} isCurrency />
          <MetricCard label="CGST" value={section.subtotal.cgst} isCurrency />
          <MetricCard label="SGST" value={section.subtotal.sgst} isCurrency />
          <MetricCard label="Cess" value={section.subtotal.cess} isCurrency />
        </MetricGrid>
      )}
      <DataTable columns={taxColumns} data={rows} />
    </div>
  );
};

const renderSupplySection = (title: string, section: any) => {
  if (!section) return null;
  const sources = Object.entries(section.source_tables || {}).map(([key, val]) => ({
    label: formatLabel(key),
    ...(val || {}),
  }));

  return (
    <div className="space-y-2">
      <h5 className="text-[11px] font-semibold uppercase text-muted-foreground">{title}</h5>
      {section.subtotal && (
        <MetricGrid>
          <MetricCard label="Taxable Value" value={section.subtotal.taxable_value} isCurrency />
          <MetricCard label="IGST" value={section.subtotal.igst} isCurrency />
          <MetricCard label="CGST" value={section.subtotal.cgst} isCurrency />
          <MetricCard label="SGST" value={section.subtotal.sgst} isCurrency />
          <MetricCard label="Cess" value={section.subtotal.cess} isCurrency />
        </MetricGrid>
      )}
      {sources.length > 0 && (
        <DataTable columns={taxColumns} data={sources} />
      )}
    </div>
  );
};

const renderInterStateSection = (title: string, section: any) => {
  if (!section) return null;
  const posRows = (section.subtotal || []).map((row: any, idx: number) => ({
    key: idx,
    place_of_supply: row.place_of_supply,
    taxable_value: row.taxable_value,
    igst: row.igst,
  }));

  return (
    <div className="space-y-2">
      <h5 className="text-[11px] font-semibold uppercase text-muted-foreground">{title}</h5>
      {posRows.length > 0 && (
        <DataTable
          columns={[
            { key: 'place_of_supply', label: 'POS' },
            { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
            { key: 'igst', label: 'IGST', type: 'currency' },
          ]}
          data={posRows}
        />
      )}
    </div>
  );
};

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
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Supply Details</h4>
                    {renderTaxBlock('Outward taxable supplies', d.supply_details.outward_taxable_supplies)}
                    {renderTaxBlock('Outward zero rated', d.supply_details.outward_zero_rated)}
                    {renderTaxBlock('Outward nil/exempt/non-GST', d.supply_details.outward_nil_exempt_non_gst)}
                    {renderTaxBlock('Outward non-GST', d.supply_details.outward_non_gst)}
                    {renderTaxBlock('Inward reverse charge', d.supply_details.inward_reverse_charge)}
                  </div>
                )}

                {d.inter_state_supplies && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Inter-State Supplies</h4>
                    {['unregistered_persons','composition_dealers','uin_holders'].map(key => (
                      (d.inter_state_supplies[key]?.length > 0) && (
                        <div key={key} className="space-y-1">
                          <h5 className="text-[11px] font-semibold uppercase text-muted-foreground">{key.replace(/_/g,' ')}</h5>
                          <DataTable
                            columns={[
                              { key: 'place_of_supply', label: 'POS' },
                              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
                              { key: 'igst', label: 'IGST', type: 'currency' },
                            ]}
                            data={d.inter_state_supplies[key]}
                          />
                        </div>
                      )
                    ))}
                  </div>
                )}

                {d.eligible_itc && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Eligible ITC</h4>
                    {['itc_available','itc_ineligible','itc_reversed'].map(key => (
                      Array.isArray(d.eligible_itc[key]) && d.eligible_itc[key].length > 0 && (
                        <div key={key}>
                          <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1">{key.replace(/_/g,' ')}</h5>
                          <DataTable
                            columns={[
                              { key: 'label', label: 'Type' },
                              { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
                              { key: 'igst', label: 'IGST', type: 'currency' },
                              { key: 'cgst', label: 'CGST', type: 'currency' },
                              { key: 'sgst', label: 'SGST', type: 'currency' },
                              { key: 'cess', label: 'Cess', type: 'currency' },
                            ]}
                            data={d.eligible_itc[key]}
                          />
                        </div>
                      )
                    ))}
                    {d.eligible_itc.itc_net && (
                      <div>
                        <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1">Net ITC</h5>
                        <MetricGrid>
                          <MetricCard label="Taxable Value" value={d.eligible_itc.itc_net.taxable_value} isCurrency />
                          <MetricCard label="IGST" value={d.eligible_itc.itc_net.igst} isCurrency />
                          <MetricCard label="CGST" value={d.eligible_itc.itc_net.cgst} isCurrency />
                          <MetricCard label="SGST" value={d.eligible_itc.itc_net.sgst} isCurrency />
                          <MetricCard label="Cess" value={d.eligible_itc.itc_net.cess} isCurrency />
                        </MetricGrid>
                      </div>
                    )}
                  </div>
                )}

                {d.inward_supplies?.rows && d.inward_supplies.rows.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Inward Supplies</h4>
                    <DataTable
                      columns={[
                        { key: 'type', label: 'Type' },
                        { key: 'inter_state', label: 'Inter State', type: 'currency' },
                        { key: 'intra_state', label: 'Intra State', type: 'currency' },
                      ]}
                      data={d.inward_supplies.rows}
                    />
                  </div>
                )}

                {d.interest_and_late_fee && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Interest & Late Fee</h4>
                    {renderTaxBlock('Interest', d.interest_and_late_fee.interest)}
                    {renderTaxBlock('Late Fee', d.interest_and_late_fee.late_fee)}
                  </div>
                )}

                {d.tax_payment && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Tax Payment</h4>

                    {Array.isArray(d.tax_payment.net_tax_payable) && d.tax_payment.net_tax_payable.length > 0 && (
                      <div>
                        <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1">Net Tax Payable</h5>
                        <DataTable
                          columns={[
                            { key: 'transaction_description', label: 'Description' },
                            { key: 'liability_ledger_id', label: 'Ledger ID' },
                            { key: 'igst', label: 'IGST', type: 'currency' },
                            { key: 'cgst', label: 'CGST', type: 'currency' },
                            { key: 'sgst', label: 'SGST', type: 'currency' },
                            { key: 'cess', label: 'Cess', type: 'currency' },
                          ]}
                          data={d.tax_payment.net_tax_payable.map((r: any) => ({
                            transaction_description: r.transaction_description,
                            liability_ledger_id: r.liability_ledger_id,
                            igst: r.igst?.tax,
                            cgst: r.cgst?.tax,
                            sgst: r.sgst?.tax,
                            cess: r.cess?.tax,
                          }))}
                        />
                      </div>
                    )}

                    {Array.isArray(d.tax_payment.tax_payable) && d.tax_payment.tax_payable.length > 0 && (
                      <div>
                        <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1">Tax Payable</h5>
                        <DataTable
                          columns={[
                            { key: 'transaction_description', label: 'Description' },
                            { key: 'liability_ledger_id', label: 'Ledger ID' },
                            { key: 'igst', label: 'IGST', type: 'currency' },
                            { key: 'cgst', label: 'CGST', type: 'currency' },
                            { key: 'sgst', label: 'SGST', type: 'currency' },
                            { key: 'cess', label: 'Cess', type: 'currency' },
                          ]}
                          data={d.tax_payment.tax_payable.map((r: any) => ({
                            transaction_description: r.transaction_description,
                            liability_ledger_id: r.liability_ledger_id,
                            igst: r.igst?.tax,
                            cgst: r.cgst?.tax,
                            sgst: r.sgst?.tax,
                            cess: r.cess?.tax,
                          }))}
                        />
                      </div>
                    )}

                    {Array.isArray(d.tax_payment.cash_paid) && d.tax_payment.cash_paid.length > 0 && (
                      <div>
                        <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1">Cash Paid</h5>
                        <DataTable
                          columns={[
                            { key: 'transaction_type', label: 'Type' },
                            { key: 'liability_ledger_id', label: 'Ledger ID' },
                            { key: 'igst_paid', label: 'IGST Paid', type: 'currency' },
                            { key: 'cgst_paid', label: 'CGST Paid', type: 'currency' },
                            { key: 'sgst_paid', label: 'SGST Paid', type: 'currency' },
                            { key: 'cess_paid', label: 'Cess Paid', type: 'currency' },
                          ]}
                          data={d.tax_payment.cash_paid}
                        />
                      </div>
                    )}

                    {d.tax_payment.itc_utilised && (
                      <div>
                        <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1">ITC Utilised</h5>
                        <MetricGrid>
                          <MetricCard label="Ledger ID" value={d.tax_payment.itc_utilised.liability_ledger_id} />
                          <MetricCard label="IGST from IGST" value={d.tax_payment.itc_utilised.igst_from_igst} isCurrency />
                          <MetricCard label="CGST from CGST" value={d.tax_payment.itc_utilised.cgst_from_cgst} isCurrency />
                          <MetricCard label="SGST from SGST" value={d.tax_payment.itc_utilised.sgst_from_sgst} isCurrency />
                          <MetricCard label="IGST from CGST" value={d.tax_payment.itc_utilised.igst_from_cgst} isCurrency />
                          <MetricCard label="IGST from SGST" value={d.tax_payment.itc_utilised.igst_from_sgst} isCurrency />
                          <MetricCard label="CGST from IGST" value={d.tax_payment.itc_utilised.cgst_from_igst} isCurrency />
                          <MetricCard label="SGST from IGST" value={d.tax_payment.itc_utilised.sgst_from_igst} isCurrency />
                          <MetricCard label="Cess from Cess" value={d.tax_payment.itc_utilised.cess_from_cess} isCurrency />
                        </MetricGrid>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>

      <DashboardSection id="gstr3b-auto" title="GSTR-3B Auto Liability" loading={loading}>
        {autoLiability.length === 0 ? <EmptyState /> : (() => {
          const auto = autoLiability[0]?.auto_calculated_liability;
          if (!auto) return <EmptyState />;

          const metaCards = [
            { label: 'Return Period', value: auto.return_period },
            { label: 'R1 Filed', value: auto.r1_filed_date || '—' },
            { label: 'R2B Generated', value: auto.r2b_gen_date || '—' },
            { label: 'R3B Generated', value: auto.r3b_gen_date || '—' },
            { label: 'Status', value: auto.status_cd },
          ];

          return (
            <div className="space-y-4">
              <MetricGrid>
                {metaCards.map((card, idx) => (
                  <MetricCard key={idx} label={card.label} value={card.value} />
                ))}
              </MetricGrid>

              {Array.isArray(auto.errors) && auto.errors.length > 0 && (
                <pre className="text-xs bg-amber-100 text-amber-900 p-3 rounded overflow-x-auto">{JSON.stringify(auto.errors, null, 2)}</pre>
              )}

              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">Eligible ITC</h4>
                {renderItcSection('Import of goods (4A1)', auto.eligible_itc?.itc_4a1_import_goods)}
                {renderItcSection('Inward reverse charge (4A3)', auto.eligible_itc?.itc_4a3_inward_reverse_charge)}
                {renderItcSection('Inward ISD (4A4)', auto.eligible_itc?.itc_4a4_inward_isd)}
                {renderItcSection('All other ITC (4A5)', auto.eligible_itc?.itc_4a5_all_other_itc)}
                {renderItcSection('Ineligible (4D2)', auto.eligible_itc?.itc_4d2_ineligible)}
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">Supply Details</h4>
                {renderSupplySection('3.1(a) Taxable outward', auto.supply_details?.osup_3_1a_taxable_outward)}
                {renderSupplySection('3.1(b) Zero-rated', auto.supply_details?.osup_3_1b_zero_rated_supply)}
                {renderSupplySection('3.1(c) Nil/Exempt/Non-GST', auto.supply_details?.osup_3_1c_nil_exempt_non_gst)}
                {renderSupplySection('3.1(e) Non-GST outward', auto.supply_details?.osup_3_1e_non_gst_outward)}
                {renderSupplySection('3.1(d) Inward reverse charge', auto.supply_details?.isup_3_1d_inward_reverse_charge)}
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">Inter-State Supplies (3.2)</h4>
                {renderInterStateSection('Unregistered', auto.inter_state_supplies?.osup_unreg_3_2_unregistered)}
                {renderInterStateSection('Composition', auto.inter_state_supplies?.osup_comp_3_2_composition)}
                {renderInterStateSection('UIN Holders', auto.inter_state_supplies?.osup_uin_3_2_uin_holders)}
              </div>
            </div>
          );
        })()}
      </DashboardSection>
    </>
  );
}
