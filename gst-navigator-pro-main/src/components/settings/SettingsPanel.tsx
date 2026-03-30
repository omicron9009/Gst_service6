import { useState } from 'react';
import { useApp } from '@/context/AppContext';
import type { AppSettings } from '@/types/client';
import { testServiceApi, testDbProxy } from '@/lib/api';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { Settings, CheckCircle, XCircle } from 'lucide-react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsPanel({ open, onOpenChange }: Props) {
  const { state, dispatch } = useApp();
  const { toast } = useToast();
  const [form, setForm] = useState<AppSettings>(state.settings);
  const [testingService, setTestingService] = useState(false);
  const [testingDb, setTestingDb] = useState(false);

  const handleSave = () => {
    dispatch({ type: 'SET_SETTINGS', payload: form });
    toast({ title: 'Settings saved' });
    onOpenChange(false);
  };

  const handleTestService = async () => {
    setTestingService(true);
    // Save temporarily so test uses new values
    localStorage.setItem('gst_settings', JSON.stringify(form));
    const ok = await testServiceApi();
    toast({
      title: ok ? 'Service API Connected ✓' : 'Service API Unreachable',
      variant: ok ? 'default' : 'destructive',
    });
    setTestingService(false);
  };

  const handleTestDb = async () => {
    setTestingDb(true);
    localStorage.setItem('gst_settings', JSON.stringify(form));
    const ok = await testDbProxy();
    toast({
      title: ok ? 'DB Proxy Connected ✓' : 'DB Proxy Unreachable',
      variant: ok ? 'default' : 'destructive',
    });
    setTestingDb(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[450px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          <div className="rounded-lg border p-4 space-y-4">
            <h3 className="text-sm font-semibold">Service API</h3>
            <div className="space-y-1.5">
              <Label>URL</Label>
              <Input value={form.serviceApiUrl} onChange={e => setForm({ ...form, serviceApiUrl: e.target.value })} />
            </div>
            <Button variant="outline" size="sm" onClick={handleTestService} disabled={testingService}>
              {testingService ? 'Testing...' : 'Test Connection'}
            </Button>
          </div>

          <div className="rounded-lg border p-4 space-y-4">
            <h3 className="text-sm font-semibold">DB Proxy</h3>
            <div className="space-y-1.5">
              <Label>URL</Label>
              <Input value={form.dbProxyUrl} onChange={e => setForm({ ...form, dbProxyUrl: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Username</Label>
              <Input value={form.dbProxyUser} onChange={e => setForm({ ...form, dbProxyUser: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Password</Label>
              <Input type="password" value={form.dbProxyPass} onChange={e => setForm({ ...form, dbProxyPass: e.target.value })} />
            </div>
            <Button variant="outline" size="sm" onClick={handleTestDb} disabled={testingDb}>
              {testingDb ? 'Testing...' : 'Test Connection'}
            </Button>
          </div>

          <Button onClick={handleSave} className="w-full">Save Settings</Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
