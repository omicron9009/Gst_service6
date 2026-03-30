import { useState } from 'react';
import { useApp } from '@/context/AppContext';
import { generateOTP, verifyOTP, refreshSession } from '@/lib/api';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { KeyRound, Send, CheckCircle, RefreshCw } from 'lucide-react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AuthPanel({ open, onOpenChange }: Props) {
  const { activeClient, dispatch } = useApp();
  const { toast } = useToast();
  const [step, setStep] = useState<'generate' | 'verify'>('generate');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);

  if (!activeClient) return null;

  const handleGenerateOTP = async () => {
    setLoading(true);
    try {
      const res = await generateOTP(activeClient.username, activeClient.gstin);
      if (res.success) {
        toast({ title: 'OTP Sent', description: 'OTP sent to registered mobile number' });
        setStep('verify');
      } else {
        toast({ title: 'Error', description: res.message || 'Failed to generate OTP', variant: 'destructive' });
      }
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    if (otp.length !== 6) return;
    setLoading(true);
    try {
      const res = await verifyOTP(activeClient.username, activeClient.gstin, otp);
      if (res.success && res.data) {
        dispatch({
          type: 'UPDATE_CLIENT',
          payload: {
            ...activeClient,
            sessionToken: res.data.access_token,
            sessionExpiry: res.data.session_expiry,
          },
        });
        toast({ title: 'Session Established ✓', description: 'You can now fetch GST data' });
        setStep('generate');
        setOtp('');
        onOpenChange(false);
      } else {
        toast({ title: 'Verification Failed', description: res.message || 'Invalid OTP', variant: 'destructive' });
      }
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const res = await refreshSession(activeClient.gstin);
      if (res.success && res.data) {
        dispatch({
          type: 'UPDATE_CLIENT',
          payload: {
            ...activeClient,
            sessionToken: res.data.access_token,
            sessionExpiry: res.data.session_expiry,
          },
        });
        toast({ title: 'Session Refreshed ✓' });
      } else {
        toast({ title: 'Refresh Failed', description: res.message, variant: 'destructive' });
      }
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[450px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" />
            Authentication — {activeClient.label}
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          <div className="rounded-lg border p-4 space-y-4">
            <h3 className="text-sm font-semibold">GSTIN: <span className="font-mono">{activeClient.gstin}</span></h3>

            {step === 'generate' ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Generate an OTP to authenticate with the GST portal.</p>
                <Button onClick={handleGenerateOTP} disabled={loading} className="w-full gap-2">
                  <Send className="h-4 w-4" />
                  {loading ? 'Sending...' : 'Generate OTP'}
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <Label htmlFor="otp">Enter 6-digit OTP</Label>
                <Input
                  id="otp"
                  placeholder="000000"
                  maxLength={6}
                  className="font-mono text-center text-lg tracking-[0.5em]"
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                />
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setStep('generate')} className="flex-1">Back</Button>
                  <Button onClick={handleVerifyOTP} disabled={loading || otp.length !== 6} className="flex-1 gap-2">
                    <CheckCircle className="h-4 w-4" />
                    {loading ? 'Verifying...' : 'Verify'}
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-lg border p-4 space-y-3">
            <h3 className="text-sm font-semibold">Session Management</h3>
            <Button variant="outline" onClick={handleRefresh} disabled={loading} className="w-full gap-2">
              <RefreshCw className="h-4 w-4" />
              Refresh Session
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
