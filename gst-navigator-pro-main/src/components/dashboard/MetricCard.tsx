import { ReactNode } from 'react';
import { formatCurrency, formatValue } from '@/lib/formatters';

interface Props {
  label: string;
  value: string | number | null | undefined | Record<string, any>;
  isCurrency?: boolean;
  className?: string;
}

export function MetricCard({ label, value, isCurrency, className = '' }: Props) {
  const display = typeof value === 'object'
    ? formatValue(value, 'text')
    : isCurrency
    ? formatCurrency(value as number)
    : formatValue(value, 'text');

  return (
    <div className={`metric-card ${className}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{display}</div>
    </div>
  );
}

export function MetricGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">{children}</div>;
}
