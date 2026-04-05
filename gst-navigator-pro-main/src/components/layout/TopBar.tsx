import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '@/context/AppContext';
import { maskGSTIN } from '@/lib/validators';
import { useDbProxy } from '@/hooks/useDbProxy';
import { downloadMonthlyReport } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { AuthPanel } from '@/components/auth/AuthPanel';
import { FetchModal } from '@/components/fetch/FetchModal';
import { PeriodSelector } from '@/components/layout/PeriodSelector';
import { Button } from '@/components/ui/button';
import { KeyRound, RefreshCw, Download, FileDown, FileSearch } from 'lucide-react';

export function TopBar() {
  const { state, activeClient, getSessionStatusForClient } = useApp();
  const { refreshData, loading } = useDbProxy();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [authOpen, setAuthOpen] = useState(false);
  const [fetchOpen, setFetchOpen] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);

  const sessionStatus = activeClient ? getSessionStatusForClient(activeClient.gstin) : 'none';

  if (!activeClient) {
    return (
      <header className="flex h-14 items-center justify-center border-b bg-card px-6">
        <p className="text-sm text-muted-foreground">Select a client from the sidebar to get started</p>
      </header>
    );
  }

  const handleReportDownload = async () => {
    if (!activeClient || !state.selectedPeriod) {
      toast({ title: 'Select a period first', description: 'Choose month and year to generate the report.', variant: 'destructive' });
      return;
    }

    setReportLoading(true);
    try {
      const { year, month } = state.selectedPeriod;
      const blob = await downloadMonthlyReport(activeClient.gstin, year, month);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${activeClient.gstin}_${year}-${month}_report.html`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast({ title: 'Report downloaded', description: 'Branded monthly HTML report saved.' });
    } catch (err: any) {
      toast({ title: 'Report failed', description: err?.message || 'Unable to download report.', variant: 'destructive' });
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <>
      <header className="flex h-14 items-center gap-4 border-b bg-card px-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-semibold truncate">{activeClient.label}</h2>
            <span className="text-xs font-mono text-muted-foreground">{maskGSTIN(activeClient.gstin)}</span>
            <span className={`status-badge ${sessionStatus === 'active' ? 'status-active' : sessionStatus === 'expired' ? 'status-expired' : 'status-none'}`}>
              {sessionStatus === 'active' ? '● Active' : sessionStatus === 'expired' ? '● Expired' : '● No Session'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setAuthOpen(true)}>
            <KeyRound className="h-3.5 w-3.5" />
            Login / OTP
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="gap-1.5"
            onClick={handleReportDownload}
            disabled={reportLoading || !state.selectedPeriod}
          >
            <FileDown className={`h-3.5 w-3.5 ${reportLoading ? 'animate-spin' : ''}`} />
            Generate Report
          </Button>
          <Button size="sm" className="gap-1.5" onClick={() => setFetchOpen(true)}>
            <Download className="h-3.5 w-3.5" />
            Fetch All Data
          </Button>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => navigate('/reconcile-2b')}>
            <FileSearch className="h-3.5 w-3.5" />
            Reconcile 2B
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => state.selectedPeriod && refreshData(activeClient.gstin, state.selectedPeriod.year, state.selectedPeriod.month)}
            disabled={loading || !state.selectedPeriod}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </header>

      <div className="flex h-10 items-center justify-between border-b bg-muted/30 px-6">
        <span className="text-xs text-muted-foreground">
          {activeClient.gstin && (
            <>Data for {activeClient.gstin}</>
          )}
        </span>
        <PeriodSelector />
      </div>

      <AuthPanel open={authOpen} onOpenChange={setAuthOpen} />
      <FetchModal open={fetchOpen} onOpenChange={setFetchOpen} />
    </>
  );
}
