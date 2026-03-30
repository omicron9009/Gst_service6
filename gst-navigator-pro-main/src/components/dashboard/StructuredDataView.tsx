import { Fragment } from 'react';
import { DataTable, type DataTableColumn } from '@/components/dashboard/DataTable';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { Badge } from '@/components/ui/badge';
import { formatNumber } from '@/lib/formatters';

interface Props {
  value: any;
  title?: string;
  depth?: number;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function isPrimitive(value: any): boolean {
  return value == null || ['string', 'number', 'boolean'].includes(typeof value);
}

function isCurrencyLikeKey(key: string): boolean {
  return /(amount|value|tax|igst|cgst|sgst|cess|turnover|itc|credit|payable|paid|fee|interest|taxable)/i.test(key);
}

function formatPrimitive(value: any): string {
  if (value == null || value === '') return '-';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    return Number.isInteger(value)
      ? formatNumber(value)
      : value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return String(value);
}

function buildColumns(rows: Record<string, any>[]): DataTableColumn[] {
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row).filter((key) => key !== '__meta'))));
  return keys.map((key) => {
    const values = rows.map((row) => row[key]).filter((value) => value !== undefined && value !== null);
    const allNumbers = values.length > 0 && values.every((value) => typeof value === 'number');
    return {
      key,
      label: humanizeKey(key),
      type: allNumbers ? (isCurrencyLikeKey(key) ? 'currency' : 'number') : undefined,
    };
  });
}

export function StructuredDataView({ value, title, depth = 0 }: Props) {
  const titleClassName = depth === 0
    ? 'text-xs font-semibold uppercase tracking-wide text-muted-foreground'
    : 'text-sm font-semibold text-foreground';

  if (value == null) {
    return (
      <div className="rounded-lg border border-dashed bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
        {title && <div className={titleClassName}>{title}</div>}
        <div className={title ? 'mt-2' : ''}>No data available</div>
      </div>
    );
  }

  if (Array.isArray(value)) {
    const arrayTitle = title ? <div className={titleClassName}>{title}</div> : null;

    if (value.length === 0) {
      return (
        <div className="rounded-lg border border-dashed bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
          {arrayTitle}
          <div className={title ? 'mt-2' : ''}>No entries</div>
        </div>
      );
    }

    if (value.every((item) => isPrimitive(item))) {
      return (
        <div className="space-y-2">
          {arrayTitle}
          <div className="flex flex-wrap gap-2">
            {value.map((item, index) => (
              <Badge key={index} variant="secondary">
                {formatPrimitive(item)}
              </Badge>
            ))}
          </div>
        </div>
      );
    }

    if (value.every((item) => item && typeof item === 'object' && !Array.isArray(item))) {
      const rows = value as Record<string, any>[];
      return (
        <div className="space-y-2">
          {arrayTitle}
          <DataTable columns={buildColumns(rows)} data={rows} pageSize={10} />
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {arrayTitle}
        <div className="rounded-lg border bg-muted/20 p-3 text-sm text-muted-foreground">
          {value.length} entries
        </div>
      </div>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value).filter(([key]) => key !== '__meta');
    const primitiveEntries = entries.filter(([, item]) => isPrimitive(item));
    const nestedEntries = entries.filter(([, item]) => !isPrimitive(item));

    return (
      <div className="space-y-3">
        {title && <div className={titleClassName}>{title}</div>}

        {primitiveEntries.length > 0 && (
          <MetricGrid>
            {primitiveEntries.map(([key, item]) => (
              <MetricCard
                key={key}
                label={humanizeKey(key)}
                value={typeof item === 'number' ? item : formatPrimitive(item)}
                isCurrency={typeof item === 'number' && isCurrencyLikeKey(key)}
              />
            ))}
          </MetricGrid>
        )}

        {nestedEntries.map(([key, item]) => (
          <div key={key} className="rounded-xl border bg-muted/10 p-3">
            <StructuredDataView value={item} title={humanizeKey(key)} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <Fragment>
      {title && <div className={titleClassName}>{title}</div>}
      <div className="rounded-lg border bg-muted/20 px-3 py-2 text-sm">{formatPrimitive(value)}</div>
    </Fragment>
  );
}
