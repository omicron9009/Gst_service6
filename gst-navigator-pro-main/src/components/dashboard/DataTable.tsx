import { useState, useMemo } from 'react';
import { formatCurrency, formatNumber } from '@/lib/formatters';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Column {
  key: string;
  label: string;
  type?: 'currency' | 'number' | 'text';
  width?: string;
}

interface Props {
  columns: Column[];
  data: any[];
  pageSize?: number;
}

export function DataTable({ columns, data, pageSize = 25 }: Props) {
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(data.length / pageSize);
  const paginated = useMemo(() => data.slice(page * pageSize, (page + 1) * pageSize), [data, page, pageSize]);
  const showPagination = data.length > 50;

  const formatCell = (value: any, type?: string) => {
    if (value == null || value === '') return '—';

    // Handle objects/arrays safely
    if (typeof value === 'object') {
      try {
        const str = JSON.stringify(value);
        return str.length > 50 ? str.substring(0, 47) + '...' : str;
      } catch {
        return '[object Object]';
      }
    }

    switch (type) {
      case 'currency':
        const numCurrency = Number(value);
        return !isNaN(numCurrency) ? formatCurrency(numCurrency) : String(value);
      case 'number':
        const numNumber = Number(value);
        return !isNaN(numNumber) ? formatNumber(numNumber) : String(value);
      default:
        return String(value);
    }
  };

  return (
    <div>
      <ScrollArea className="w-full">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col.key} style={col.width ? { minWidth: col.width } : undefined}>{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map((row, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col.key} className={col.type === 'currency' || col.type === 'number' ? 'text-right font-mono' : ''}>
                      {formatCell(row[col.key], col.type)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ScrollArea>
      {showPagination && (
        <div className="flex items-center justify-between border-t px-3 py-2 text-xs text-muted-foreground">
          <span>{data.length} records — Page {page + 1} of {totalPages}</span>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
