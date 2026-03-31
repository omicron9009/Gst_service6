import { useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import { useDbProxy } from '@/hooks/useDbProxy';
import { PeriodIndicator } from '@/components/dashboard/PeriodIndicator';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { Gstr1Sections } from '@/components/gstr1/Gstr1Sections';
import { Gstr2aSections } from '@/components/gstr2a/Gstr2aSections';
import { Gstr2bSections } from '@/components/gstr2b/Gstr2bSections';
import { Gstr3bSections } from '@/components/gstr3b/Gstr3bSections';
import { Gstr9Sections } from '@/components/gstr9/Gstr9Sections';
import { LedgerSections } from '@/components/ledgers/LedgerSections';
import { ReturnStatusSection } from '@/components/returnStatus/ReturnStatusSection';
import { Accordion } from '@/components/ui/accordion';
import { ScrollArea } from '@/components/ui/scroll-area';

const ALL_SECTIONS = [
  'gstr1-summary', 'gstr1-b2b', 'gstr1-b2cs', 'gstr1-b2cl', 'gstr1-cdn', 'gstr1-exp',
  'gstr1-nil', 'gstr1-hsn', 'gstr1-doc', 'gstr1-at-txp',
  'gstr2a-b2b', 'gstr2a-cdn', 'gstr2a-doc', 'gstr2a-isd', 'gstr2a-tds',
  'gstr2b-summary', 'gstr2b-docs', 'gstr2b-regen',
  'gstr3b-details', 'gstr3b-auto',
  'gstr9-auto', 'gstr9-8a', 'gstr9-details',
  'return-status',
  'ledger-balance', 'ledger-cash', 'ledger-itc', 'ledger-liability',
];

export default function Index() {
  const { activeClient } = useApp();
  const { refreshData } = useDbProxy();

  useEffect(() => {
    if (activeClient?.gstin) {
      refreshData(activeClient.gstin);
    }
  }, [activeClient?.gstin]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <TopBar />
        <ScrollArea className="flex-1">
          <div className="p-6 max-w-[1400px] mx-auto">
            {!activeClient ? (
              <div className="flex items-center justify-center h-[60vh]">
                <div className="text-center space-y-2">
                  <h2 className="text-xl font-semibold text-muted-foreground">Welcome to GST Dashboard</h2>
                  <p className="text-sm text-muted-foreground">Add a client from the sidebar to begin</p>
                </div>
              </div>
            ) : (
              <>
                <PeriodIndicator />
                <div className="mt-6">
                  <Accordion type="multiple" defaultValue={ALL_SECTIONS} className="space-y-0">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">GSTR-1</h3>
                <Gstr1Sections />

                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-6 mb-3">GSTR-2A</h3>
                <Gstr2aSections />

                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-6 mb-3">GSTR-2B</h3>
                <Gstr2bSections />

                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-6 mb-3">GSTR-3B</h3>
                <Gstr3bSections />

                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-6 mb-3">GSTR-9</h3>
                <Gstr9Sections />

                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-6 mb-3">Return Status</h3>
                <ReturnStatusSection />

                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-6 mb-3">Ledgers</h3>
                <LedgerSections />
                  </Accordion>
                </div>
              </>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
