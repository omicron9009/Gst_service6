import { CalendarRange, Database } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { useDbProxy } from '@/hooks/useDbProxy';
import { formatTimestamp } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const MONTH_LABELS: Record<string, string> = {
  '01': 'Jan',
  '02': 'Feb',
  '03': 'Mar',
  '04': 'Apr',
  '05': 'May',
  '06': 'Jun',
  '07': 'Jul',
  '08': 'Aug',
  '09': 'Sep',
  '10': 'Oct',
  '11': 'Nov',
  '12': 'Dec',
};

function monthLabel(month: string | null): string {
  return month ? (MONTH_LABELS[month] || month) : 'No month';
}

export function PeriodBar() {
  const { activeClient } = useApp();
  const { availability, selection, setPeriodSelection, snapshot } = useDbProxy();

  if (!activeClient) return null;

  const availableMonths = selection.year ? availability.monthsByYear[selection.year] || [] : [];
  const monthlySummary = selection.year && selection.month
    ? `${monthLabel(selection.month)} ${selection.year}`
    : 'No monthly dataset selected';
  const annualSummary = selection.financialYear
    ? `FY ${selection.financialYear}`
    : 'No annual dataset selected';

  return (
    <div className="border-b bg-background/95">
      <div className="px-6 py-4">
        <div className="mx-auto grid max-w-[1400px] gap-4 lg:grid-cols-[1.25fr_1fr_1fr]">
          <div className="rounded-xl border bg-card p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <CalendarRange className="h-4 w-4" />
              Data Period
            </div>
            <div className="mt-2 text-sm font-medium text-foreground">
              Showing monthly data for {monthlySummary} and annual data for {annualSummary}.
            </div>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>Monthly years in DB: {availability.monthlyYears.length || 0}</span>
              <span>Financial years in DB: {availability.financialYears.length || 0}</span>
              <span>Snapshot loaded: {snapshot.fetchedAt ? formatTimestamp(snapshot.fetchedAt) : '-'}</span>
            </div>
          </div>

          <div className="rounded-xl border bg-card p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Database className="h-4 w-4" />
              Monthly Filters
            </div>
            <div className="mt-3 space-y-3">
              <div>
                <div className="mb-1 text-xs text-muted-foreground">Year available in database</div>
                <Select
                  value={selection.year || undefined}
                  onValueChange={(year) => setPeriodSelection({
                    year,
                    month: availability.monthsByYear[year]?.[0] || null,
                  })}
                  disabled={availability.monthlyYears.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="No monthly data" />
                  </SelectTrigger>
                  <SelectContent>
                    {availability.monthlyYears.map((year) => (
                      <SelectItem key={year} value={year}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="mb-2 text-xs text-muted-foreground">Months available for selected year</div>
                <div className="flex flex-wrap gap-2">
                  {availableMonths.length === 0 ? (
                    <span className="text-xs text-muted-foreground">No stored months for this year.</span>
                  ) : availableMonths.map((month) => (
                    <Button
                      key={month}
                      type="button"
                      size="sm"
                      variant={selection.month === month ? 'default' : 'outline'}
                      onClick={() => setPeriodSelection({ month })}
                    >
                      {monthLabel(month)}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border bg-card p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Database className="h-4 w-4" />
              Annual Filters
            </div>
            <div className="mt-3">
              <div className="mb-1 text-xs text-muted-foreground">Financial year available in database</div>
              <Select
                value={selection.financialYear || undefined}
                onValueChange={(financialYear) => setPeriodSelection({ financialYear })}
                disabled={availability.financialYears.length === 0}
              >
                <SelectTrigger>
                  <SelectValue placeholder="No annual data" />
                </SelectTrigger>
                <SelectContent>
                  {availability.financialYears.map((financialYear) => (
                    <SelectItem key={financialYear} value={financialYear}>
                      FY {financialYear}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
