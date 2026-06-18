import { useState, useCallback } from 'react';
import { useApp } from '@/context/AppContext';
import { serviceGet } from '@/lib/api';
import { useDbProxy } from '@/hooks/useDbProxy';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { CheckCircle, XCircle, Loader2, Download } from 'lucide-react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface CallStatus {
  id: string;
  label: string;
  status: 'pending' | 'fetching' | 'done' | 'error';
  message?: string;
}

const MONTHS = Array.from({ length: 12 }, (_, i) => ({ value: String(i + 1).padStart(2, '0'), label: new Date(2000, i).toLocaleString('en', { month: 'long' }) }));

export function FetchModal({ open, onOpenChange }: Props) {
  const { activeClient } = useApp();
  const { refreshData, loadAvailablePeriods } = useDbProxy();
  const { dispatch } = useApp();
  const { toast } = useToast();

  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [month, setMonth] = useState(String(new Date().getMonth() + 1).padStart(2, '0'));
  const [fy, setFy] = useState('2024-25');
  const [referenceId, setReferenceId] = useState('');
  const [summaryType, setSummaryType] = useState('short');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [fileNumber, setFileNumber] = useState('');
  const [counterpartyGstin, setCounterpartyGstin] = useState('');
  const [actionRequired, setActionRequired] = useState('');
  const [stateCode, setStateCode] = useState('');

  const [statuses, setStatuses] = useState<CallStatus[]>([]);
  const [running, setRunning] = useState(false);

  if (!activeClient) return null;

  const gstin = activeClient.gstin;
  const token = activeClient.sessionToken;

  // After any fetch group completes, refresh DB data for the fetched period
  // and reload available periods so the new period appears in the selector.
  const postFetchRefresh = async () => {
    // Set the selected period to the one just fetched so the dashboard shows it
    dispatch({ type: 'SET_SELECTED_PERIOD', payload: { year, month } });
    await loadAvailablePeriods(gstin);
    await refreshData(gstin, year, month);
  };

  const updateStatus = (id: string, status: CallStatus['status'], message?: string) => {
    setStatuses(prev => prev.map(s => s.id === id ? { ...s, status, message } : s));
  };

  const runCall = async (id: string, path: string) => {
    updateStatus(id, 'fetching');
    try {
      const res = await serviceGet(path, token);
      if (res.success === false) {
        updateStatus(id, 'error', res.message || 'Failed');
      } else {
        updateStatus(id, 'done', 'OK');
      }
    } catch (err: any) {
      updateStatus(id, 'error', err.message);
    }
  };

  const buildQS = (params: Record<string, string>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v) qs.append(k, v); });
    const s = qs.toString();
    return s ? `?${s}` : '';
  };

  const runGroup = async (calls: { id: string; label: string; path: string }[]) => {
    setStatuses(prev => [...prev, ...calls.map(c => ({ id: c.id, label: c.label, status: 'pending' as const }))]);
    await Promise.allSettled(calls.map(c => runCall(c.id, c.path)));
  };

  const handleFetchGstr1 = async () => {
    const calls = [
      { id: 'g1-summary', label: 'GSTR-1 Summary', path: `/gstr1/summary/${gstin}/${year}/${month}${buildQS({ summary_type: summaryType })}` },
      { id: 'g1-b2b', label: 'GSTR-1 B2B', path: `/gstr1/b2b/${gstin}/${year}/${month}${buildQS({ action_required: actionRequired, from_date: fromDate, counterparty_gstin: counterpartyGstin })}` },
      { id: 'g1-b2csa', label: 'GSTR-1 B2CSA', path: `/gstr1/b2csa/${gstin}/${year}/${month}` },
      { id: 'g1-b2cs', label: 'GSTR-1 B2CS', path: `/gstr1/b2cs/${gstin}/${year}/${month}` },
      { id: 'g1-b2cl', label: 'GSTR-1 B2CL', path: `/gstr1/b2cl/${gstin}/${year}/${month}${buildQS({ state_code: stateCode })}` },
      { id: 'g1-cdnr', label: 'GSTR-1 CDNR', path: `/gstr1/cdnr/${gstin}/${year}/${month}${buildQS({ action_required: actionRequired, from: fromDate })}` },
      { id: 'g1-cdnur', label: 'GSTR-1 CDNUR', path: `/gstr1/cdnur/${gstin}/${year}/${month}` },
      { id: 'g1-exp', label: 'GSTR-1 EXP', path: `/gstr1/exp/${gstin}/${year}/${month}` },
      { id: 'g1-nil', label: 'GSTR-1 NIL', path: `/gstr1/nil/${gstin}/${year}/${month}` },
      { id: 'g1-hsn', label: 'GSTR-1 HSN', path: `/gstr1/hsn/${gstin}/${year}/${month}` },
      { id: 'g1-doc', label: 'GSTR-1 Doc Issue', path: `/gstr1/doc-issue/${gstin}/${year}/${month}` },
      { id: 'g1-at', label: 'GSTR-1 Advance Tax', path: `/gstr1/advance-tax/${gstin}/${year}/${month}` },
      { id: 'g1-txp', label: 'GSTR-1 TXP', path: `/gstr1/gstr1/${gstin}/${year}/${month}/txp${buildQS({ counterparty_gstin: counterpartyGstin, action_required: actionRequired, from: fromDate })}` },
    ];
    await runGroup(calls);
    await postFetchRefresh();
  };

  const handleFetchGstr2a = async () => {
    const calls = [
      { id: 'g2a-b2b', label: 'GSTR-2A B2B', path: `/gstr2A/b2b/${gstin}/${year}/${month}` },
      { id: 'g2a-b2ba', label: 'GSTR-2A B2BA', path: `/gstr2A/b2ba/${gstin}/${year}/${month}${buildQS({ counterparty_gstin: counterpartyGstin })}` },
      { id: 'g2a-cdn', label: 'GSTR-2A CDN', path: `/gstr2A/cdn/${gstin}/${year}/${month}${buildQS({ counterparty_gstin: counterpartyGstin, from_date: fromDate })}` },
      { id: 'g2a-cdna', label: 'GSTR-2A CDNA', path: `/gstr2A/cdna/${gstin}/${year}/${month}${buildQS({ counterparty_gstin: counterpartyGstin })}` },
      { id: 'g2a-doc', label: 'GSTR-2A Document', path: `/gstr2A/document/${gstin}/${year}/${month}` },
      { id: 'g2a-isd', label: 'GSTR-2A ISD', path: `/gstr2A/isd/${gstin}/${year}/${month}${buildQS({ counterparty_gstin: counterpartyGstin })}` },
      { id: 'g2a-tds', label: 'GSTR-2A TDS', path: `/gstr2A/gstr2a/${gstin}/${year}/${month}/tds` },
    ];
    await runGroup(calls);
    await postFetchRefresh();
  };

  const handleFetchGstr2b = async () => {
    const calls = [
      { id: 'g2b-main', label: 'GSTR-2B', path: `/gstr2B/gstr2b/${gstin}/${year}/${month}${buildQS({ file_number: fileNumber })}` },
    ];
    if (referenceId) {
      calls.push({ id: 'g2b-regen', label: 'GSTR-2B Regen Status', path: `/gstr2B/gstr2b/${gstin}/regenerate/status?reference_id=${encodeURIComponent(referenceId)}` });
    }
    await runGroup(calls);
    await postFetchRefresh();
  };

  const handleFetchGstr3b = async () => {
    const calls = [
      { id: 'g3b-details', label: 'GSTR-3B Details', path: `/gstr3B/gstr3b/${gstin}/${year}/${month}` },
      { id: 'g3b-auto', label: 'GSTR-3B Auto Liability', path: `/gstr3B/gstr3b/${gstin}/${year}/${month}/auto-liability-calc` },
    ];
    await runGroup(calls);
    await postFetchRefresh();
  };

  const handleFetchGstr9 = async () => {
    const calls = [
      { id: 'g9-auto', label: 'GSTR-9 Auto Calculated', path: `/gstr9/gstr9/${gstin}/auto-calculated?financial_year=${encodeURIComponent(fy)}` },
      { id: 'g9-details', label: 'GSTR-9 Details', path: `/gstr9/gstr9/${gstin}?financial_year=${encodeURIComponent(fy)}` },
    ];
    if (fileNumber) {
      calls.push({ id: 'g9-8a', label: 'GSTR-9 Table 8A', path: `/gstr9/gstr9/${gstin}/table-8a?financial_year=${encodeURIComponent(fy)}&file_number=${fileNumber}` });
    }
    await runGroup(calls);
    await postFetchRefresh();
  };

  const handleFetchReturnStatus = async () => {
    if (!referenceId) { toast({ title: 'Reference ID required', variant: 'destructive' }); return; }
    await runGroup([{
      id: 'ret-status', label: 'Return Status', path: `/return_status/returns/${gstin}/${year}/${month}/status?reference_id=${encodeURIComponent(referenceId)}`
    }]);
    await postFetchRefresh();
  };

  const handleFetchLedgers = async () => {
    const calls = [
      { id: 'led-bal', label: 'Cash+ITC Balance', path: `/ledgers/ledgers/${gstin}/${year}/${month}/balance` },
    ];
    if (fromDate && toDate) {
      calls.push(
        { id: 'led-cash', label: 'Cash Ledger', path: `/ledgers/ledgers/${gstin}/cash?from=${encodeURIComponent(fromDate)}&to=${encodeURIComponent(toDate)}` },
        { id: 'led-itc', label: 'ITC Ledger', path: `/ledgers/ledgers/${gstin}/itc?from=${encodeURIComponent(fromDate)}&to=${encodeURIComponent(toDate)}` },
        { id: 'led-liab', label: 'Liability Ledger', path: `/ledgers/ledgers/${gstin}/tax/${year}/${month}?from=${encodeURIComponent(fromDate)}&to=${encodeURIComponent(toDate)}` },
      );
    }
    await runGroup(calls);
    await postFetchRefresh();
  };

  const handleFetchAll = async () => {
    setRunning(true);
    setStatuses([]);
    await handleFetchGstr1();
    await handleFetchGstr2a();
    await handleFetchGstr2b();
    await handleFetchGstr3b();
    await handleFetchGstr9();
    await handleFetchLedgers();
    await postFetchRefresh();
    setRunning(false);
    toast({ title: 'Fetch Complete', description: 'All data has been fetched and refreshed from DB' });
  };

  const StatusIcon = ({ status }: { status: CallStatus['status'] }) => {
    switch (status) {
      case 'done': return <CheckCircle className="h-4 w-4 text-success" />;
      case 'error': return <XCircle className="h-4 w-4 text-destructive" />;
      case 'fetching': return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
      default: return <div className="h-4 w-4 rounded-full border-2 border-border" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5 text-primary" />
            Fetch GST Data — {activeClient.label}
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="flex-1 pr-2">
          <div className="space-y-4">
            {/* Common Inputs */}
            <div className="grid grid-cols-4 gap-3 rounded-lg border p-4">
              <div className="space-y-1">
                <Label className="text-xs">Year</Label>
                <Input value={year} onChange={e => setYear(e.target.value)} placeholder="2024" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Month</Label>
                <Select value={month} onValueChange={setMonth}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{MONTHS.map(m => <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Financial Year</Label>
                <Input value={fy} onChange={e => setFy(e.target.value)} placeholder="2024-25" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Reference ID <span className="text-muted-foreground">(opt)</span></Label>
                <Input value={referenceId} onChange={e => setReferenceId(e.target.value)} />
              </div>
            </div>

            {/* Optional Filters */}
            <div className="grid grid-cols-4 gap-3 rounded-lg border p-4">
              <div className="space-y-1">
                <Label className="text-xs">Summary Type <span className="text-muted-foreground">(opt)</span></Label>
                <Select value={summaryType} onValueChange={setSummaryType}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="short">Short</SelectItem>
                    <SelectItem value="long">Long</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">From Date <span className="text-muted-foreground">(opt)</span></Label>
                <Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">To Date <span className="text-muted-foreground">(opt)</span></Label>
                <Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">File Number <span className="text-muted-foreground">(opt)</span></Label>
                <Input value={fileNumber} onChange={e => setFileNumber(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Counterparty GSTIN <span className="text-muted-foreground">(opt)</span></Label>
                <Input value={counterpartyGstin} onChange={e => setCounterpartyGstin(e.target.value)} className="font-mono" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Action Required <span className="text-muted-foreground">(opt)</span></Label>
                <Input value={actionRequired} onChange={e => setActionRequired(e.target.value)} placeholder="Y or N" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">State Code <span className="text-muted-foreground">(opt)</span></Label>
                <Input value={stateCode} onChange={e => setStateCode(e.target.value)} />
              </div>
            </div>

            {/* Fetch All button */}
            <Button onClick={handleFetchAll} disabled={running} className="w-full gap-2">
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {running ? 'Fetching...' : 'Fetch All Groups'}
            </Button>

            {/* Individual group buttons */}
            <Accordion type="multiple" defaultValue={['gstr1','gstr2a','gstr2b','gstr3b','gstr9','ret','ledgers']}>
              {[
                { value: 'gstr1', label: 'GSTR-1 (13 calls)', handler: handleFetchGstr1 },
                { value: 'gstr2a', label: 'GSTR-2A (7 calls)', handler: handleFetchGstr2a },
                { value: 'gstr2b', label: 'GSTR-2B (1-2 calls)', handler: handleFetchGstr2b },
                { value: 'gstr3b', label: 'GSTR-3B (2 calls)', handler: handleFetchGstr3b },
                { value: 'gstr9', label: 'GSTR-9 (2-3 calls)', handler: handleFetchGstr9 },
                { value: 'ret', label: 'Return Status (1 call)', handler: handleFetchReturnStatus },
                { value: 'ledgers', label: 'Ledgers (1-4 calls)', handler: handleFetchLedgers },
              ].map(g => (
                <AccordionItem key={g.value} value={g.value}>
                  <AccordionTrigger className="text-sm font-medium py-2">{g.label}</AccordionTrigger>
                  <AccordionContent>
                    <Button size="sm" variant="outline" onClick={g.handler} disabled={running} className="mb-2">
                      Fetch {g.label.split(' (')[0]}
                    </Button>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>

            {/* Progress */}
            {statuses.length > 0 && (
              <div className="rounded-lg border p-3 space-y-1">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Progress</h4>
                {statuses.map(s => (
                  <div key={s.id} className="flex items-center gap-2 text-sm py-0.5">
                    <StatusIcon status={s.status} />
                    <span className="flex-1 truncate">{s.label}</span>
                    {s.message && <span className={`text-xs ${s.status === 'error' ? 'text-destructive' : 'text-muted-foreground'}`}>{s.message}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
