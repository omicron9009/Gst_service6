import { useMemo } from 'react';
import { useApp } from '@/context/AppContext';
import { useDbProxy } from '@/hooks/useDbProxy';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import type { Period } from '@/types/client';

interface TableAvailability {
  [tableName: string]: boolean;
}

export function PeriodIndicator() {
  const { state, dispatch, activeClient } = useApp();
  const { getData, refreshData, loadAvailablePeriods } = useDbProxy();

  const periodInfo = useMemo(() => {
    // Use a default period if none is selected
    const defaultPeriod: Period = {
      year: new Date().getFullYear().toString(),
      month: String(new Date().getMonth() + 1).padStart(2, '0'),
    };

    const period = state.selectedPeriod || defaultPeriod;
    const month = period.month;
    const year = period.year;

    const monthNames = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];

    const monthName = monthNames[parseInt(month) - 1] || 'Unknown';

    // Get all data for current period to show what's available
    const summary = getData('gstr1_summary');
    const b2b = getData('gstr1_b2b');
    const b2cs = getData('gstr1_b2cs');
    const b2csa = getData('gstr1_b2csa');
    const cdnr = getData('gstr1_cdnr');
    const cdnur = getData('gstr1_cdnur');
    const docIssue = getData('gstr1_doc_issue');
    const hsn = getData('gstr1_hsn');
    const nil = getData('gstr1_nil');
    const b2cl = getData('gstr1_b2cl');
    const exp = getData('gstr1_exp');
    const txp = getData('gstr1_txp');
    const at = getData('gstr1_advance_tax');
    const gstr2a_b2b = getData('gstr2a_b2b');
    const gstr2a_cdn = getData('gstr2a_cdn');
    const gstr2a_doc = getData('gstr2a_document');
    const gstr2a_isd = getData('gstr2a_isd');
    const gstr2a_tds = getData('gstr2a_tds');
    const gstr2b = getData('gstr2b');
    const gstr3b = getData('gstr3b_details');
    const gstr9_auto = getData('gstr9_auto_calculated');
    const gstr9_details = getData('gstr9_details');
    const gstr9_8a = getData('gstr9_table8a');

    // Count available data sections (only non-empty arrays)
    const availableSections = [
      summary.length > 0 ? 'GSTR-1' : null,
      b2b.length > 0 ? 'B2B' : null,
      b2cs.length > 0 ? 'B2CS' : null,
      b2csa.length > 0 ? 'B2CSA' : null,
      cdnr.length > 0 ? 'CDNR' : null,
      cdnur.length > 0 ? 'CDNUR' : null,
      docIssue.length > 0 ? 'Doc Issue' : null,
      hsn.length > 0 ? 'HSN' : null,
      nil.length > 0 ? 'Nil' : null,
      b2cl.length > 0 ? 'B2CL' : null,
      exp.length > 0 ? 'Export' : null,
      txp.length > 0 ? 'TXP' : null,
      at.length > 0 ? 'AT' : null,
      gstr2a_b2b.length > 0 ? 'GSTR-2A (B2B)' : null,
      gstr2a_cdn.length > 0 ? 'GSTR-2A (CDN)' : null,
      gstr2a_doc.length > 0 ? 'GSTR-2A (Doc)' : null,
      gstr2a_isd.length > 0 ? 'GSTR-2A (ISD)' : null,
      gstr2a_tds.length > 0 ? 'GSTR-2A (TDS)' : null,
      gstr2b.length > 0 ? 'GSTR-2B' : null,
      gstr3b.length > 0 ? 'GSTR-3B' : null,
      gstr9_auto.length > 0 ? 'GSTR-9 (Auto)' : null,
      gstr9_details.length > 0 ? 'GSTR-9 (Details)' : null,
      gstr9_8a.length > 0 ? 'GSTR-9 (8A)' : null,
    ].filter(Boolean);

    // Use available periods from state, or default to current period
    const availablePeriods = state.availablePeriods.length > 0
      ? state.availablePeriods
      : [defaultPeriod];

    return {
      period,
      month,
      year,
      monthName,
      availableSections,
      sectionCount: availableSections.length,
      availablePeriods,
    };
  }, [state.selectedPeriod, state.availablePeriods, getData]);

  const handlePrevPeriod = () => {
    const periods = periodInfo.availablePeriods;
    const currentIndex = periods.findIndex(
      p => p.month === periodInfo.period.month && p.year === periodInfo.period.year
    );
    if (currentIndex > 0) {
      const nextPeriod = periods[currentIndex - 1];
      dispatch({
        type: 'SET_SELECTED_PERIOD',
        payload: nextPeriod,
      });
      if (activeClient?.gstin) {
        refreshData(activeClient.gstin, nextPeriod.year, nextPeriod.month);
      }
    }
  };

  const handleNextPeriod = () => {
    const periods = periodInfo.availablePeriods;
    const currentIndex = periods.findIndex(
      p => p.month === periodInfo.period.month && p.year === periodInfo.period.year
    );
    if (currentIndex < periods.length - 1) {
      const nextPeriod = periods[currentIndex + 1];
      dispatch({
        type: 'SET_SELECTED_PERIOD',
        payload: nextPeriod,
      });
      if (activeClient?.gstin) {
        refreshData(activeClient.gstin, nextPeriod.year, nextPeriod.month);
      }
    }
  };

  const currentIndex = periodInfo.availablePeriods.findIndex(
    p => p.month === periodInfo.period.month && p.year === periodInfo.period.year
  ) + 1;
  const totalPeriods = periodInfo.availablePeriods.length;

  if (!activeClient) {
    return null;
  }

  return (
    <Card className="w-full bg-gradient-to-r from-slate-50 to-slate-100 border-slate-200">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-900">
              Data for {activeClient.gstin}
            </h2>
          </div>
          <span className="text-xs text-slate-600 bg-white px-2 py-1 rounded">
            Period {currentIndex} of {totalPeriods}
          </span>
        </div>

        {totalPeriods === 0 && (
          <div className="mb-3">
            <Button
              size="sm"
              variant="outline"
              onClick={() => activeClient?.gstin && loadAvailablePeriods(activeClient.gstin)}
            >
              Load Available Periods
            </Button>
          </div>
        )}

        {/* Period Display and Navigation */}
        <div className="flex items-center justify-between mb-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevPeriod}
            disabled={currentIndex <= 1}
            className="h-8 w-8 p-0"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <div className="flex-1 text-center">
            <div className="text-2xl font-bold text-slate-900">
              {periodInfo.monthName} {periodInfo.year}
            </div>
            <div className="text-xs text-slate-600">
              Period: {String(periodInfo.month).padStart(2, '0')}/{periodInfo.year}
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleNextPeriod}
            disabled={currentIndex >= totalPeriods}
            className="h-8 w-8 p-0"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Available Sections */}
        <div className="bg-white rounded-md p-3 border border-slate-200">
          <div className="text-xs font-semibold text-slate-600 mb-2">
            Available Data ({periodInfo.sectionCount} sections):
          </div>
          <div className="flex flex-wrap gap-2">
            {periodInfo.availableSections.length > 0 ? (
              periodInfo.availableSections.map((section) => (
                <span
                  key={section}
                  className="inline-block bg-green-50 text-green-700 text-xs font-medium px-3 py-1 rounded-full border border-green-200"
                >
                  ✓ {section}
                </span>
              ))
            ) : (
              <span className="text-xs text-amber-700 bg-amber-50 px-3 py-1 rounded-full border border-amber-200">
                No data available for this period
              </span>
            )}
          </div>
        </div>

        {/* Period List */}
        {periodInfo.availablePeriods.length > 1 && (
          <div className="mt-3 pt-3 border-t border-slate-200">
            <div className="text-xs font-semibold text-slate-600 mb-2">
              All Available Periods:
            </div>
            <div className="flex flex-wrap gap-1">
              {periodInfo.availablePeriods.map((period: Period) => {
                const m = String(period.month).padStart(2, '0');
                const y = period.year;
                const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                const mName = monthNames[parseInt(period.month) - 1];
                const isSelected = period.month === periodInfo.period.month && period.year === periodInfo.period.year;

                return (
                  <button
                    key={`${period.year}-${period.month}`}
                    onClick={() => {
                      dispatch({ type: 'SET_SELECTED_PERIOD', payload: period });
                      if (activeClient?.gstin) {
                        refreshData(activeClient.gstin, period.year, period.month);
                      }
                    }}
                    className={`text-xs px-2 py-1 rounded transition-colors ${
                      isSelected
                        ? 'bg-blue-600 text-white font-semibold'
                        : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                    }`}
                  >
                    {mName} {y}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
