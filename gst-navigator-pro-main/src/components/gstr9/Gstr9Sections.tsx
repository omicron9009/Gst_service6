import { useDbProxy } from '@/hooks/useDbProxy';
import { DashboardSection } from '@/components/dashboard/DashboardSection';
import { DataTable } from '@/components/dashboard/DataTable';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { JsonDisplay } from '@/components/dashboard/JsonDisplay';

const taxColumns = [
  { key: 'label', label: 'Category' },
  { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
  { key: 'igst', label: 'IGST', type: 'currency' },
  { key: 'cgst', label: 'CGST', type: 'currency' },
  { key: 'sgst', label: 'SGST', type: 'currency' },
  { key: 'cess', label: 'Cess', type: 'currency' },
];

const summaryColumns = [
  { key: 'label', label: 'Field' },
  { key: 'value', label: 'Value', type: 'currency' },
];

const amountColumns = [
  { key: 'label', label: 'Category' },
  { key: 'amount', label: 'Amount', type: 'currency' },
];

const table9Columns = [
  { key: 'label', label: 'Component' },
  { key: 'tax_payable', label: 'Tax Payable', type: 'currency' },
  { key: 'paid_in_cash', label: 'Paid in Cash', type: 'currency' },
  { key: 'paid_via_igst_itc', label: 'Paid via IGST ITC', type: 'currency' },
  { key: 'paid_via_cgst_itc', label: 'Paid via CGST ITC', type: 'currency' },
  { key: 'paid_via_sgst_itc', label: 'Paid via SGST ITC', type: 'currency' },
  { key: 'paid_via_cess_itc', label: 'Paid via Cess ITC', type: 'currency' },
];

const table8aSummaryColumns = [
  { key: 'section', label: 'Section' },
  { key: 'invoice_count', label: 'Invoices' },
  { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
  { key: 'igst', label: 'IGST', type: 'currency' },
  { key: 'cgst', label: 'CGST', type: 'currency' },
  { key: 'sgst', label: 'SGST', type: 'currency' },
  { key: 'cess', label: 'Cess', type: 'currency' },
];

const table8aColumns = [
  { key: 'section', label: 'Section' },
  { key: 'supplier_gstin', label: 'Supplier GSTIN' },
  { key: 'return_period', label: 'Return Period' },
  { key: 'filing_date', label: 'Filing Date' },
  { key: 'invoice_number', label: 'Invoice #' },
  { key: 'invoice_date', label: 'Invoice Date' },
  { key: 'original_invoice_number', label: 'Original Inv #' },
  { key: 'note_number', label: 'Note #' },
  { key: 'note_type', label: 'Note Type' },
  { key: 'invoice_type', label: 'Invoice Type' },
  { key: 'place_of_supply', label: 'POS' },
  { key: 'reverse_charge', label: 'RC' },
  { key: 'is_eligible', label: 'Eligible' },
  { key: 'ineligibility_reason', label: 'Reason' },
  { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
  { key: 'igst', label: 'IGST', type: 'currency' },
  { key: 'cgst', label: 'CGST', type: 'currency' },
  { key: 'sgst', label: 'SGST', type: 'currency' },
  { key: 'cess', label: 'Cess', type: 'currency' },
];

const itcNonRcColumns = [
  { key: 'itc_type_label', label: 'ITC Type' },
  { key: 'igst', label: 'IGST', type: 'currency' },
  { key: 'cgst', label: 'CGST', type: 'currency' },
  { key: 'sgst', label: 'SGST', type: 'currency' },
  { key: 'cess', label: 'Cess', type: 'currency' },
];

const table17Columns = [
  { key: 'hsn_sac', label: 'HSN/SAC' },
  { key: 'description', label: 'Description' },
  { key: 'tax_rate', label: 'Rate' },
  { key: 'taxable_value', label: 'Taxable Value', type: 'currency' },
  { key: 'igst', label: 'IGST', type: 'currency' },
  { key: 'cgst', label: 'CGST', type: 'currency' },
  { key: 'sgst', label: 'SGST', type: 'currency' },
  { key: 'cess', label: 'Cess', type: 'currency' },
  { key: 'is_concessional', label: 'Concessional' },
];

const toTaxRows = (section: any, keys: string[]) => {
  if (!section) return [];
  return keys
    .map(key => {
      const block = section[key];
      if (!block) return null;
      return {
        label: key.replace(/_/g, ' '),
        taxable_value: block.taxable_value,
        igst: block.igst,
        cgst: block.cgst,
        sgst: block.sgst,
        cess: block.cess,
      };
    })
    .filter(Boolean) as any[];
};

const renderTaxTable = (title: string, section: any, keys: string[]) => {
  const rows = toTaxRows(section, keys);
  if (rows.length === 0) return null;
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">{title}</h4>
      <DataTable columns={taxColumns} data={rows} />
    </div>
  );
};

const renderAmountTable = (title: string, section: any) => {
  if (!section) return null;
  const rows = Object.entries(section)
    .filter(([k]) => k !== 'checksum')
    .map(([k, v]) => ({ label: k.replace(/_/g, ' '), amount: v as any }));
  if (rows.length === 0) return null;
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">{title}</h4>
      <DataTable columns={amountColumns} data={rows} />
    </div>
  );
};

const renderTable6 = (section: any) => {
  if (!section) return null;
  const rows = [
    { label: 'From GSTR-3B', ...section.itc_from_gstr3b },
    { label: 'From ISD', ...section.itc_from_isd },
    { label: 'TRAN-1 Credit', taxable_value: null, igst: null, cgst: section.tran1_credit?.cgst, sgst: section.tran1_credit?.sgst, cess: null },
    { label: 'TRAN-2 Credit', taxable_value: null, igst: null, cgst: section.tran2_credit?.cgst, sgst: section.tran2_credit?.sgst, cess: null },
  ].filter(r => r.label && Object.values(r).some(v => v !== undefined && v !== null));

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 6: ITC Availed</h4>
      <DataTable columns={taxColumns} data={rows as any[]} />
    </div>
  );
};

const renderTable8 = (section: any) => {
  if (!section) return null;
  return renderTaxTable('Table 8: ITC as per 2B', section, ['itc_as_per_2b']);
};

const renderTable9 = (section: any) => {
  if (!section) return null;
  const rows = [
    { label: 'IGST', ...section.igst },
    { label: 'CGST', ...section.cgst },
    { label: 'SGST', ...section.sgst },
    { label: 'Cess', ...section.cess },
    { label: 'Interest', ...section.interest },
    { label: 'Late Fee', ...section.late_fee },
  ].filter(r => r.label && Object.values(r).some(v => v !== undefined && v !== null));

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 9: Tax Paid</h4>
      <DataTable columns={table9Columns} data={rows as any[]} />
    </div>
  );
};

const toNumber = (value: any) => (value === null || value === undefined ? 0 : Number(value));

const summarizeSection = (entries: any[]) =>
  (entries || []).reduce(
    (acc, supplier) => {
      (supplier?.documents || []).forEach((doc: any) => {
        acc.taxable_value += toNumber(doc.taxable_value);
        acc.igst += toNumber(doc.igst);
        acc.cgst += toNumber(doc.cgst);
        acc.sgst += toNumber(doc.sgst);
        acc.cess += toNumber(doc.cess);
        acc.invoice_count += 1;
      });
      return acc;
    },
    { taxable_value: 0, igst: 0, cgst: 0, sgst: 0, cess: 0, invoice_count: 0 }
  );

const buildTable8aSummary = (records: any[]) => {
  const totals = {
    B2B: summarizeSection(records.flatMap(r => r?.b2b || [])),
    B2BA: summarizeSection(records.flatMap(r => r?.b2ba || [])),
    CDN: summarizeSection(records.flatMap(r => r?.cdn || [])),
  } as Record<string, any>;

  return Object.entries(totals)
    .map(([section, values]) => ({ section, ...values }))
    .filter(row => row.invoice_count > 0 || row.taxable_value > 0);
};

const flattenTable8a = (records: any[]) => {
  const rows: any[] = [];

  const pushRows = (section: string, suppliers: any[], fileNumber: string) => {
    suppliers.forEach(supplier => {
      (supplier?.documents || []).forEach((doc: any) => {
        rows.push({
          file_number: fileNumber,
          section,
          supplier_gstin: supplier.supplier_gstin,
          return_period: supplier.return_period,
          filing_date: supplier.filing_date,
          invoice_number: doc.invoice_number,
          invoice_date: doc.invoice_date,
          original_invoice_number: doc.original_invoice_number,
          note_number: doc.note_number,
          note_type: doc.note_type,
          invoice_type: doc.invoice_type,
          place_of_supply: doc.place_of_supply,
          reverse_charge: doc.reverse_charge,
          is_eligible: doc.is_eligible,
          ineligibility_reason: doc.ineligibility_reason,
          taxable_value: toNumber(doc.taxable_value),
          igst: toNumber(doc.igst),
          cgst: toNumber(doc.cgst),
          sgst: toNumber(doc.sgst),
          cess: toNumber(doc.cess),
        });
      });
    });
  };

  records.forEach(record => {
    const fileNumber = record?.file_number || record?.doc_id || record?.docid || '';
    pushRows('B2B', record?.b2b || [], fileNumber);
    pushRows('B2BA', record?.b2ba || [], fileNumber);
    pushRows('CDN', record?.cdn || [], fileNumber);
  });

  return rows;
};

const buildTaxRows = (section: any, entries: { key: string; label?: string }[]) =>
  entries
    .map(({ key, label }) => {
      const block = section?.[key];
      if (!block) return null;
      return {
        label: label || key.replace(/_/g, ' '),
        taxable_value: block.taxable_value,
        igst: block.igst,
        cgst: block.cgst,
        sgst: block.sgst,
        cess: block.cess,
      };
    })
    .filter(Boolean) as any[];

const buildAmountRows = (section: any, keys: { key: string; label?: string }[]) =>
  keys
    .map(({ key, label }) => {
      const amount = section?.[key];
      if (amount === undefined || amount === null) return null;
      return { label: label || key.replace(/_/g, ' '), amount };
    })
    .filter(Boolean) as any[];

const renderDetailsTable4 = (section: any) => {
  const rows = buildTaxRows(section, [
    { key: 'b2b_supplies', label: 'B2B Supplies' },
    { key: 'b2c_supplies', label: 'B2C Supplies' },
    { key: 'credit_notes', label: 'Credit Notes' },
    { key: 'subtotal_a_to_g1', label: 'Subtotal A-G1' },
    { key: 'subtotal_i_to_l_deductions', label: 'Subtotal I-L Deductions' },
    { key: 'net_taxable_turnover', label: 'Net Taxable Turnover' },
  ]);

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 4: Outward Taxable Supplies</h4>
      <DataTable columns={taxColumns} data={rows} pageSize={10} />
    </div>
  );
};

const renderDetailsTable5 = (section: any) => {
  if (!section) return null;

  const amountRows = buildAmountRows(section, [
    { key: 'nil_rated', label: 'Nil Rated' },
    { key: 'exempt', label: 'Exempt' },
    { key: 'non_gst', label: 'Non-GST' },
    { key: 'zero_rated', label: 'Zero Rated' },
    { key: 'sez', label: 'SEZ' },
    { key: 'reverse_charge', label: 'Reverse Charge' },
    { key: 'ecom_section_14', label: 'E-Com Sec 14' },
    { key: 'credit_notes', label: 'Credit Notes' },
    { key: 'debit_notes', label: 'Debit Notes' },
    { key: 'amendments_positive', label: 'Amendments (+)' },
    { key: 'amendments_negative', label: 'Amendments (-)' },
    { key: 'subtotal_a_to_f', label: 'Subtotal A-F' },
    { key: 'subtotal_h_to_k', label: 'Subtotal H-K' },
    { key: 'turnover_tax_not_paid', label: 'Turnover Tax Not Paid' },
  ]);

  const totalTurnoverRows = buildTaxRows(section, [
    { key: 'total_turnover', label: 'Total Turnover' },
  ]);

  if (amountRows.length === 0 && totalTurnoverRows.length === 0) return null;

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 5: Exempt / Nil / Non-GST</h4>
      {amountRows.length > 0 && <DataTable columns={amountColumns} data={amountRows} pageSize={15} />}
      {totalTurnoverRows.length > 0 && <DataTable columns={taxColumns} data={totalTurnoverRows} pageSize={5} />}
    </div>
  );
};

const renderDetailsTable6 = (section: any) => {
  if (!section) return null;

  const mainRows = buildTaxRows(section, [
    { key: 'itc_from_gstr3b', label: 'ITC from GSTR-3B' },
  ]);

  const totalsRows = buildTaxRows(section, [
    { key: 'subtotal_b_to_h', label: 'Subtotal B-H' },
    { key: 'subtotal_k_to_m', label: 'Subtotal K-M' },
    { key: 'total_itc_availed', label: 'Total ITC Availed' },
    { key: 'difference_6b_vs_3b', label: 'Difference 6B vs 3B' },
  ]);

  const nonReverseRows = Array.isArray(section.non_reverse_charge_itc) ? section.non_reverse_charge_itc : [];

  if (mainRows.length === 0 && totalsRows.length === 0 && nonReverseRows.length === 0) return null;

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 6: ITC Availed</h4>
      {mainRows.length > 0 && <DataTable columns={taxColumns} data={mainRows} pageSize={5} />}
      {nonReverseRows.length > 0 && <DataTable columns={itcNonRcColumns} data={nonReverseRows} pageSize={10} />}
      {totalsRows.length > 0 && <DataTable columns={taxColumns} data={totalsRows} pageSize={5} />}
    </div>
  );
};

const renderDetailsTable7 = (section: any) => {
  const rows = buildTaxRows(section, [
    { key: 'net_itc_available', label: 'Net ITC Available' },
    { key: 'rule_37_reversal', label: 'Rule 37 Reversal' },
    { key: 'rule_39_reversal', label: 'Rule 39 Reversal' },
    { key: 'rule_42_reversal', label: 'Rule 42 Reversal' },
    { key: 'rule_43_reversal', label: 'Rule 43 Reversal' },
    { key: 'section_17_reversal', label: 'Section 17 Reversal' },
    { key: 'tran1_reversal', label: 'TRAN-1 Reversal' },
    { key: 'tran2_reversal', label: 'TRAN-2 Reversal' },
    { key: 'total_itc_reversed', label: 'Total ITC Reversed' },
  ]);

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 7: ITC Reversed / Ineligible</h4>
      <DataTable columns={taxColumns} data={rows} pageSize={10} />
    </div>
  );
};

const renderDetailsTable8 = (section: any) => {
  const rows = buildTaxRows(section, [
    { key: 'itc_as_per_2b', label: 'ITC as per 2B' },
    { key: 'itc_net_availed', label: 'ITC Net Availed' },
    { key: 'itc_on_inward_supplies', label: 'ITC on Inward Supplies' },
    { key: 'itc_not_availed', label: 'ITC Not Availed' },
    { key: 'itc_ineligible', label: 'ITC Ineligible' },
    { key: 'itc_lapsed', label: 'ITC Lapsed' },
    { key: 'iog_itc_availed', label: 'IOG ITC Availed' },
    { key: 'iog_itc_not_availed', label: 'IOG ITC Not Availed' },
    { key: 'iog_tax_paid', label: 'IOG Tax Paid' },
    { key: 'difference_abc_2b_vs_3b', label: 'Difference ABC (2B vs 3B)' },
    { key: 'difference_gh_itc_vs_ineligible', label: 'Difference GH (ITC vs Ineligible)' },
  ]);

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 8: ITC Comparison</h4>
      <DataTable columns={taxColumns} data={rows} pageSize={12} />
    </div>
  );
};

const renderDetailsTable9 = (section: any) => {
  if (!section) return null;

  const normalizeRow = (label: string, obj: any) => ({
    label,
    tax_payable: obj?.tax_payable,
    paid_in_cash: obj?.paid_in_cash,
    paid_via_igst_itc: obj?.paid_via_igst_itc,
    paid_via_cgst_itc: obj?.paid_via_cgst_itc,
    paid_via_sgst_itc: obj?.paid_via_sgst_itc,
    paid_via_cess_itc: obj?.paid_via_cess_itc,
  });

  const rows = [
    normalizeRow('IGST', section.igst),
    normalizeRow('CGST', section.cgst),
    normalizeRow('SGST', section.sgst),
    normalizeRow('Cess', section.cess),
    normalizeRow('Interest', section.interest),
    normalizeRow('Late Fee', section.late_fee),
    normalizeRow('Penalty', section.penalty),
    normalizeRow('Other', section.other),
  ].filter(r => Object.values(r).some(v => v !== undefined && v !== null));

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 9: Tax Payable vs Paid</h4>
      <DataTable columns={table9Columns} data={rows} pageSize={10} />
    </div>
  );
};

const renderDetailsTable10 = (section: any) => {
  const rows = buildTaxRows(section, [
    { key: 'total_turnover', label: 'Total Turnover' },
  ]);

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 10: Turnover Reconciliation</h4>
      <DataTable columns={taxColumns} data={rows} pageSize={5} />
    </div>
  );
};

const renderDetailsTable17 = (section: any) => {
  const items = Array.isArray(section?.hsn_items) ? section.hsn_items : [];
  if (items.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">Table 17: HSN Summary</h4>
      <DataTable columns={table17Columns} data={items} pageSize={15} />
    </div>
  );
};

export function Gstr9Sections() {
  const { getData, loading } = useDbProxy();

  const auto = getData('gstr9_auto_calculated');
  const table8a = getData('gstr9_table8a');
  const details = getData('gstr9_details');

  const table8aData = Array.isArray(table8a) ? table8a : [];
  const table8aSummary = buildTable8aSummary(table8aData);
  const table8aRows = flattenTable8a(table8aData);

  return (
    <>
      <DashboardSection id="gstr9-auto" title="GSTR-9 Annual Return (Auto-Calculated)" loading={loading}>
        {auto.length === 0 ? <EmptyState /> : (
          <div className="space-y-4">
            {auto.map((d: any, i: number) => (
              <div key={i} className="space-y-4">
                <DataTable
                  columns={summaryColumns}
                  data={[
                    { label: 'Financial Period', value: d.financial_period },
                    { label: 'Aggregate Turnover', value: d.aggregate_turnover },
                    { label: 'HSN Min Length', value: d.hsn_min_length },
                  ]}
                  pageSize={10}
                />

                {renderTaxTable('Table 4: Outward Supplies', d.table4_outward_supplies, [
                  'b2b_supplies','b2c_supplies','exports','sez_supplies','deemed_exports','reverse_charge','ecom_operator','credit_notes','debit_notes','advances_tax_paid','amendments_positive','amendments_negative'
                ])}

                {renderAmountTable('Table 5: Exempt/Nil/Non-GST', d.table5_exempt_nil_non_gst)}

                {renderTable6(d.table6_itc_availed)}

                {renderTable8(d.table8_itc_as_per_2b)}

                {renderTable9(d.table9_tax_paid)}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>

      <DashboardSection id="gstr9-8a" title="GSTR-9 Table 8A (ITC from Suppliers)" loading={loading}>
        {table8aData.length === 0 ? <EmptyState /> : (
          <div className="space-y-3">
            <DataTable columns={table8aSummaryColumns} data={table8aSummary} pageSize={10} />
            <DataTable columns={table8aColumns} data={table8aRows} pageSize={25} />
          </div>
        )}
      </DashboardSection>

      <DashboardSection id="gstr9-details" title="GSTR-9 Details (Full Return)" loading={loading}>
        {details.length === 0 ? <EmptyState /> : (
          <div className="space-y-3">
            {details.map((d: any, i: number) => (
              <div key={i} className="space-y-3">
                {(() => {
                  const sections = d.detail_sections || {};
                  const metaRows = [
                    { label: 'Financial Period', value: sections.financial_period },
                    { label: 'Aggregate Turnover', value: sections.aggregate_turnover },
                  ].filter(row => row.value !== undefined && row.value !== null);

                  const rendered = [
                    metaRows.length > 0 ? (
                      <DataTable key="meta" columns={summaryColumns} data={metaRows} pageSize={5} />
                    ) : null,
                    renderDetailsTable4(sections.table4_outward_taxable_supplies),
                    renderDetailsTable5(sections.table5_exempt_nil_non_gst),
                    renderDetailsTable6(sections.table6_itc_availed),
                    renderDetailsTable7(sections.table7_itc_reversed),
                    renderDetailsTable8(sections.table8_itc_comparison),
                    renderDetailsTable9(sections.table9_tax_payable_vs_paid),
                    renderDetailsTable10(sections.table10_turnover_reconciliation),
                    renderDetailsTable17(sections.table17_hsn_summary),
                  ].filter(Boolean);

                  if (rendered.length === 0) {
                    return <JsonDisplay data={d.detail_sections || d} collapsible={false} maxHeight="250px" />;
                  }

                  return rendered;
                })()}
              </div>
            ))}
          </div>
        )}
      </DashboardSection>
    </>
  );
}
