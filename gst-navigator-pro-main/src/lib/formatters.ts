export function formatCurrency(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '₹0';
  return '₹' + value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '0';
  return value.toLocaleString('en-IN');
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export function formatTimestamp(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

export function formatValue(value: any, type?: 'currency' | 'number' | 'text'): string {
  if (value == null || value === '') return '—';

  // If it's an object or array, return JSON string representation
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return '[object Object]';
    }
  }

  // Type-based formatting
  if (type === 'currency') {
    const num = Number(value);
    return !isNaN(num) ? formatCurrency(num) : String(value);
  }

  if (type === 'number') {
    const num = Number(value);
    return !isNaN(num) ? formatNumber(num) : String(value);
  }

  return String(value);
}
