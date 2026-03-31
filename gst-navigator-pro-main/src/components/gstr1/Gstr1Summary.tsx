import { useMemo } from 'react';
import { formatCurrency, formatNumber } from '@/lib/formatters';
import { DataTable } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { EmptyState } from '@/components/dashboard/EmptyState';

interface Section {
  sec_nm: string;
  ttl_rec: number;
  ttl_val: number | null;
  ttl_tax: number | null;
  ttl_igst: number | null;
  ttl_cgst: number | null;
  ttl_sgst: number | null;
  ttl_cess: number | null;
  chksum: string;
  sub_sections?: Section[];
  raw?: any;
}

interface SummaryRow {
  sec_nm: string;
  ttl_rec: number;
  ttl_val: number;
  ttl_tax: number;
  ttl_igst: number;
  ttl_cgst: number;
  ttl_sgst: number;
  ttl_cess: number;
}

interface Props {
  summary: Section[];
  loading?: boolean;
}

export function Gstr1Summary({ summary, loading }: Props) {
  const { totals, sections } = useMemo(() => {
    if (!Array.isArray(summary) || summary.length === 0) {
      return { totals: null, sections: [] };
    }

    // Filter sections with actual data
    const dataSections = summary.filter(sec =>
      (sec.ttl_rec && sec.ttl_rec > 0) ||
      (sec.ttl_val && sec.ttl_val !== 0) ||
      (sec.ttl_tax && sec.ttl_tax !== 0)
    );

    // Calculate totals from all sections
    const totals = {
      totalRecords: summary.reduce((sum, s) => sum + (s.ttl_rec || 0), 0),
      totalValue: summary.reduce((sum, s) => sum + (s.ttl_val || 0), 0),
      totalTax: summary.reduce((sum, s) => sum + (s.ttl_tax || 0), 0),
      totalIGST: summary.reduce((sum, s) => sum + (s.ttl_igst || 0), 0),
      totalCGST: summary.reduce((sum, s) => sum + (s.ttl_cgst || 0), 0),
      totalSGST: summary.reduce((sum, s) => sum + (s.ttl_sgst || 0), 0),
      totalCESS: summary.reduce((sum, s) => sum + (s.ttl_cess || 0), 0),
    };

    // Normalize sections for display
    const normalized: SummaryRow[] = dataSections.map(sec => ({
      sec_nm: sec.sec_nm || 'Unknown',
      ttl_rec: sec.ttl_rec || 0,
      ttl_val: normalizeValue(sec.ttl_val),
      ttl_tax: normalizeValue(sec.ttl_tax),
      ttl_igst: normalizeValue(sec.ttl_igst),
      ttl_cgst: normalizeValue(sec.ttl_cgst),
      ttl_sgst: normalizeValue(sec.ttl_sgst),
      ttl_cess: normalizeValue(sec.ttl_cess),
    }));

    return { totals, sections: normalized };
  }, [summary]);

  if (!summary || summary.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-4">
      {/* Overall Summary Cards */}
      <MetricGrid>
        <MetricCard
          label="Total Documents"
          value={totals?.totalRecords || 0}
        />
        <MetricCard
          label="Total Invoice Value"
          value={totals?.totalValue || 0}
          isCurrency
        />
        <MetricCard
          label="Total Tax Liability"
          value={totals?.totalTax || 0}
          isCurrency
        />
        <MetricCard
          label="Total IGST"
          value={totals?.totalIGST || 0}
          isCurrency
        />
        <MetricCard
          label="Total CGST"
          value={totals?.totalCGST || 0}
          isCurrency
        />
        <MetricCard
          label="Total SGST"
          value={totals?.totalSGST || 0}
          isCurrency
        />
      </MetricGrid>

      {/* Detailed Summary Table */}
      <div className="mt-6">
        <h3 className="text-sm font-semibold mb-3">Section Wise Summary</h3>
        <DataTable
          columns={[
            { key: 'sec_nm', label: 'Section', width: '120px' },
            { key: 'ttl_rec', label: 'Records', type: 'number', width: '80px' },
            { key: 'ttl_val', label: 'Invoice Value', type: 'currency' },
            { key: 'ttl_tax', label: 'Total Tax', type: 'currency' },
            { key: 'ttl_igst', label: 'IGST', type: 'currency' },
            { key: 'ttl_cgst', label: 'CGST', type: 'currency' },
            { key: 'ttl_sgst', label: 'SGST', type: 'currency' },
            { key: 'ttl_cess', label: 'CESS', type: 'currency' },
          ]}
          data={sections}
          pageSize={50}
        />
      </div>
    </div>
  );
}

function normalizeValue(value: any): number {
  if (value === null || value === undefined) return 0;
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}
