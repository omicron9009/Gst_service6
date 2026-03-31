import { useState } from 'react';
import { useApp } from '@/context/AppContext';
import { maskGSTIN } from '@/lib/validators';
import { formatTimestamp } from '@/lib/formatters';
import { useDbProxy } from '@/hooks/useDbProxy';
import { AuthPanel } from '@/components/auth/AuthPanel';
import { FetchModal } from '@/components/fetch/FetchModal';
import { PeriodSelector } from '@/components/layout/PeriodSelector';
import { Button } from '@/components/ui/button';
import { KeyRound, RefreshCw, Download } from 'lucide-react';

export function TopBar() {
  const { activeClient, getSessionStatusForClient } = useApp();
  const { refreshData, loading } = useDbProxy();
  const [authOpen, setAuthOpen] = useState(false);
  const [fetchOpen, setFetchOpen] = useState(false);

  const sessionStatus = activeClient ? getSessionStatusForClient(activeClient.gstin) : 'none';

  if (!activeClient) {
    return (
      <header className="flex h-14 items-center justify-center border-b bg-card px-6">
        <p className="text-sm text-muted-foreground">Select a client from the sidebar to get started</p>
      </header>
    );
  }

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
          <Button size="sm" className="gap-1.5" onClick={() => setFetchOpen(true)}>
            <Download className="h-3.5 w-3.5" />
            Fetch All Data
          </Button>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => refreshData()} disabled={loading}>
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
