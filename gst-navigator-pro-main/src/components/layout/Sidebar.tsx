import { useState } from 'react';
import { useApp } from '@/context/AppContext';
import { maskGSTIN } from '@/lib/validators';
import { ClientCard } from '@/components/clients/ClientCard';
import { AddClientModal } from '@/components/clients/AddClientModal';
import { SettingsPanel } from '@/components/settings/SettingsPanel';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, Settings, BarChart3 } from 'lucide-react';

export function Sidebar() {
  const { state, dispatch } = useApp();
  const [addOpen, setAddOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <aside className="flex h-screen w-[280px] flex-col bg-[hsl(var(--sidebar-bg))] text-[hsl(var(--sidebar-fg))] shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2 px-5 py-5 border-b border-[hsl(var(--sidebar-border))]">
          <BarChart3 className="h-6 w-6 text-[hsl(var(--sidebar-accent))]" />
          <h1 className="text-lg font-bold tracking-tight">GST Dashboard</h1>
        </div>

        {/* Clients Header */}
        <div className="flex items-center justify-between px-5 py-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--sidebar-fg)/0.5)]">Clients</span>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 gap-1 text-xs text-[hsl(var(--sidebar-fg)/0.7)] hover:text-[hsl(var(--sidebar-fg))] hover:bg-[hsl(var(--sidebar-muted))]"
            onClick={() => setAddOpen(true)}
          >
            <Plus className="h-3.5 w-3.5" />
            Add
          </Button>
        </div>

        {/* Client List */}
        <ScrollArea className="flex-1 px-3">
          {state.clients.length === 0 ? (
            <div className="px-2 py-8 text-center text-sm text-[hsl(var(--sidebar-fg)/0.4)]">
              No clients found in database
            </div>
          ) : (
            <div className="space-y-1">
              {state.clients.map(client => (
                <ClientCard key={client.id} client={client} />
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Settings */}
        <div className="border-t border-[hsl(var(--sidebar-border))] px-3 py-3">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-xs text-[hsl(var(--sidebar-fg)/0.6)] hover:text-[hsl(var(--sidebar-fg))] hover:bg-[hsl(var(--sidebar-muted))]"
            onClick={() => setSettingsOpen(true)}
          >
            <Settings className="h-4 w-4" />
            Settings
          </Button>
        </div>
      </aside>

      <AddClientModal open={addOpen} onOpenChange={setAddOpen} />
      <SettingsPanel open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
