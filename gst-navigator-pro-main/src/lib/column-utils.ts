interface Column {
  key: string;
  label: string;
  type?: 'currency' | 'number' | 'text';
  width?: string;
}

// Keywords that indicate a column should be formatted as currency
const CURRENCY_KEYWORDS = ['tax', 'value', 'gst', 'igst', 'cgst', 'sgst', 'cess', 'amount', 'price', 'cost', 'total'];

// Keywords that indicate a column should be formatted as a number
const NUMBER_KEYWORDS = ['count', 'number', 'qty', 'quantity', 'rate', 'percent', 'percentage', 'id'];

export function detectColumnType(key: string): 'currency' | 'number' | 'text' {
  const lowerKey = key.toLowerCase();

  // Check for currency patterns
  if (CURRENCY_KEYWORDS.some(kw => lowerKey.includes(kw))) {
    return 'currency';
  }

  // Check for number patterns
  if (NUMBER_KEYWORDS.some(kw => lowerKey.includes(kw))) {
    return 'number';
  }

  return 'text';
}

export function detectColumnTypes(data: Record<string, any>[], existingColumns?: Column[]): Column[] {
  if (data.length === 0) return [];

  const firstRow = data[0];
  const columns: Column[] = [];

  Object.keys(firstRow).forEach(key => {
    // Check if column already exists with type info
    const existing = existingColumns?.find(c => c.key === key);
    if (existing && existing.type) {
      columns.push(existing);
      return;
    }

    const detectedType = detectColumnType(key);
    columns.push({
      key,
      label: key.replace(/_/g, ' '),
      type: detectedType !== 'text' ? detectedType : undefined,
      width: key.toLowerCase().includes('gstin') ? '160px' : undefined,
    });
  });

  return columns;
}
