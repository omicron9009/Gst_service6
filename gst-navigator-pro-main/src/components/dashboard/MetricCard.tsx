import { ReactNode } from 'react';
import { formatCurrency } from '@/lib/formatters';

interface Props {
  label: string;
  value: string | number | Record<string, any> | any[] | null | undefined;
  isCurrency?: boolean;
  className?: string;
}

function summarizeValue(
  value: string | number | Record<string, any> | any[] | null | undefined,
  isCurrency?: boolean,
): string {
  if (value == null || value === '') return '-';
  if (isCurrency) return formatCurrency(Number(value));

  if (Array.isArray(value)) {
    if (value.length === 0) return '[]';
    return `${value.length} entries`;
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    if (entries.length === 0) return '{}';
    const [firstKey, firstValue] = entries[0];
    return `${firstKey.replace(/_/g, ' ')}: ${String(firstValue ?? '-')}`;
  }

  return String(value);
}

export function MetricCard({ label, value, isCurrency, className = '' }: Props) {
  return (
    <div className={`metric-card ${className}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{summarizeValue(value, isCurrency)}</div>
    </div>
  );
}

export function MetricGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">{children}</div>;
}
