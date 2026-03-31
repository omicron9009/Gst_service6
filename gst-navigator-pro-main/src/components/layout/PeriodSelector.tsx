import { useMemo } from 'react';
import { useApp } from '@/context/AppContext';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function PeriodSelector() {
  const { state, dispatch } = useApp();
  const { selectedPeriod, availablePeriods } = state;

  // Group periods by year
  const periodsByYear = useMemo(() => {
    const grouped: Record<string, string[]> = {};
    availablePeriods.forEach(p => {
      if (!grouped[p.year]) grouped[p.year] = [];
      grouped[p.year].push(p.month);
    });
    // Sort years and months
    Object.keys(grouped).forEach(year => {
      grouped[year].sort();
    });
    return grouped;
  }, [availablePeriods]);

  const years = useMemo(() => Object.keys(periodsByYear).sort(), [periodsByYear]);
  const months = selectedPeriod ? periodsByYear[selectedPeriod.year] || [] : [];

  const handleYearChange = (year: string) => {
    const monthsForYear = periodsByYear[year];
    if (monthsForYear && monthsForYear.length > 0) {
      dispatch({
        type: 'SET_SELECTED_PERIOD',
        payload: { year, month: monthsForYear[0] }
      });
    }
  };

  const handleMonthChange = (month: string) => {
    if (selectedPeriod) {
      dispatch({
        type: 'SET_SELECTED_PERIOD',
        payload: { year: selectedPeriod.year, month }
      });
    }
  };

  if (availablePeriods.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground whitespace-nowrap">Period:</span>

      <Select value={selectedPeriod?.year || ''} onValueChange={handleYearChange}>
        <SelectTrigger className="w-24 h-8 text-xs">
          <SelectValue placeholder="Year" />
        </SelectTrigger>
        <SelectContent>
          {years.map(year => (
            <SelectItem key={year} value={year}>
              {year}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={selectedPeriod?.month || ''} onValueChange={handleMonthChange}>
        <SelectTrigger className="w-24 h-8 text-xs">
          <SelectValue placeholder="Month" />
        </SelectTrigger>
        <SelectContent>
          {months.map(month => {
            const monthName = new Date(`2024-${month}-01`).toLocaleString('en-IN', { month: 'short' });
            return (
              <SelectItem key={month} value={month}>
                {monthName} ({month})
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </div>
  );
}
