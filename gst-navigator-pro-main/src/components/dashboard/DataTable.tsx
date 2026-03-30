import { ReactNode, useEffect, useMemo, useState } from 'react';
import { formatCurrency, formatNumber } from '@/lib/formatters';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface DataTableColumn {
  key: string;
  label: string;
  type?: 'currency' | 'number' | 'text';
  width?: string;
  render?: (value: any, row: any) => ReactNode;
}

interface Props {
  columns: DataTableColumn[];
  data: any[];
  pageSize?: number;
}

function summarizeStructuredValue(value: any): string {
  if (value == null || value === '') return '-';

  if (Array.isArray(value)) {
    if (value.length === 0) return '[]';
    if (value.every((item) => item == null || ['string', 'number', 'boolean'].includes(typeof item))) {
      return value.join(', ');
    }
    return `${value.length} items`;
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    if (entries.length === 0) return '{}';

    const preview = entries
      .filter(([, item]) => item == null || ['string', 'number', 'boolean'].includes(typeof item))
      .slice(0, 3)
      .map(([key, item]) => `${key.replace(/_/g, ' ')}: ${item ?? '-'}`);

    if (preview.length > 0) {
      return preview.join(' | ');
    }

    try {
      return JSON.stringify(value).slice(0, 120);
    } catch {
      return `${entries.length} fields`;
    }
  }

  return String(value);
}

export function DataTable({ columns, data, pageSize = 25 }: Props) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(data.length / pageSize));
  const paginated = useMemo(
    () => data.slice(page * pageSize, (page + 1) * pageSize),
    [data, page, pageSize],
  );
  const showPagination = data.length > 50;

  useEffect(() => {
    setPage(0);
  }, [data, pageSize]);

  const formatCell = (value: any, type?: string) => {
    if (value == null || value === '') return '-';
    switch (type) {
      case 'currency':
        return formatCurrency(Number(value));
      case 'number':
        return formatNumber(Number(value));
      default:
        return summarizeStructuredValue(value);
    }
  };

  return (
    <div>
      <ScrollArea className="w-full">
        <div className="min-w-max">
          <table className="data-table min-w-full">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col.key} style={col.width ? { minWidth: col.width } : undefined}>
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map((row, index) => (
                <tr key={index}>
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={col.type === 'currency' || col.type === 'number' ? 'text-right font-mono' : ''}
                    >
                      {col.render ? col.render(row[col.key], row) : formatCell(row[col.key], col.type)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
      {showPagination && (
        <div className="flex items-center justify-between border-t px-3 py-2 text-xs text-muted-foreground">
          <span>{data.length} records - Page {page + 1} of {totalPages}</span>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setPage((currentPage) => Math.max(0, currentPage - 1))}
              disabled={page === 0}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setPage((currentPage) => Math.min(totalPages - 1, currentPage + 1))}
              disabled={page >= totalPages - 1}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
