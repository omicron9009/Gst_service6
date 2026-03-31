import { useState } from 'react';
import { useApp } from '@/context/AppContext';
import { validateGSTIN } from '@/lib/validators';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddClientModal({ open, onOpenChange }: Props) {
  const { dispatch } = useApp();
  const [label, setLabel] = useState('');
  const [username, setUsername] = useState('');
  const [gstin, setGstin] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    if (!label.trim() || !username.trim() || !gstin.trim()) {
      setError('All fields are required');
      return;
    }
    if (!validateGSTIN(gstin.toUpperCase())) {
      setError('Invalid GSTIN format');
      return;
    }
    dispatch({
      type: 'ADD_CLIENT',
      payload: {
        id: crypto.randomUUID(),
        label: label.trim(),
        username: username.trim(),
        gstin: gstin.toUpperCase().trim(),
        sessionToken: null,
        sessionExpiry: null,
        addedAt: new Date().toISOString(),
      },
    });
    setLabel(''); setUsername(''); setGstin(''); setError('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>Add New Client</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="label">Client Label</Label>
            <Input id="label" placeholder="e.g. ABC Enterprises" value={label} onChange={e => setLabel(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="username">GST Username</Label>
            <Input id="username" placeholder="GST portal username" value={username} onChange={e => setUsername(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="gstin">GSTIN</Label>
            <Input id="gstin" placeholder="27AAAAA0000A1Z5" maxLength={15} className="font-mono uppercase" value={gstin} onChange={e => setGstin(e.target.value.toUpperCase())} />
            <p className="text-xs text-muted-foreground">15-character GST Identification Number</p>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSubmit}>Add Client</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
