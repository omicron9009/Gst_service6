import { useState } from 'react';
import { useApp } from '@/context/AppContext';
import { maskGSTIN } from '@/lib/validators';
import { useDbProxy } from '@/hooks/useDbProxy';
import { AuthPanel } from '@/components/auth/AuthPanel';
import { FetchModal } from '@/components/fetch/FetchModal';
import { Button } from '@/components/ui/button';
import { Download, KeyRound, RefreshCw } from 'lucide-react';

export function TopBar() {
  const { activeClient, getSessionStatusForClient } = useApp();
  const { refreshData, loading } = useDbProxy();
  const [authOpen, setAuthOpen] = useState(false);
  const [fetchOpen, setFetchOpen] = useState(false);

  const sessionStatus = activeClient ? getSessionStatusForClient(activeClient.gstin) : 'none';

  if (!activeClient) {
    return (
      <header className="flex h-14 items-center justify-center border-b bg-card px-6">
        <p className="text-sm text-muted-foreground">Select a client from the sidebar to get started.</p>
      </header>
    );
  }

  return (
    <>
      <header className="flex h-14 items-center gap-4 border-b bg-card px-6">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <h2 className="truncate text-base font-semibold">{activeClient.label}</h2>
            <span className="text-xs font-mono text-muted-foreground">{maskGSTIN(activeClient.gstin)}</span>
            <span
              className={`status-badge ${
                sessionStatus === 'active'
                  ? 'status-active'
                  : sessionStatus === 'expired'
                    ? 'status-expired'
                    : 'status-none'
              }`}
            >
              {sessionStatus === 'active'
                ? 'Active Session'
                : sessionStatus === 'expired'
                  ? 'Expired Session'
                  : 'No Session'}
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

      <AuthPanel open={authOpen} onOpenChange={setAuthOpen} />
      <FetchModal open={fetchOpen} onOpenChange={setFetchOpen} />
    </>
  );
}
