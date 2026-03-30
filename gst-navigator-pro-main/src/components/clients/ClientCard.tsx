import { useApp } from '@/context/AppContext';
import type { GSTClient } from '@/types/client';
import { maskGSTIN } from '@/lib/validators';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MoreVertical, Pencil, Trash2 } from 'lucide-react';

interface Props {
  client: GSTClient;
}

export function ClientCard({ client }: Props) {
  const { state, dispatch, getSessionStatusForClient } = useApp();
  const isActive = state.activeClientId === client.id;
  const status = getSessionStatusForClient(client.gstin);

  return (
    <div
      className={`group relative flex cursor-pointer items-start gap-3 rounded-lg px-3 py-2.5 transition-colors ${
        isActive ? 'bg-[hsl(var(--sidebar-muted))]' : 'hover:bg-[hsl(var(--sidebar-muted)/0.5)]'
      }`}
      onClick={() => dispatch({ type: 'SET_ACTIVE_CLIENT', payload: client.id })}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[hsl(var(--sidebar-accent)/0.2)] text-sm font-bold text-[hsl(var(--sidebar-accent))]">
        {client.label.charAt(0).toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium truncate">{client.label}</p>
        <p className="text-xs font-mono text-[hsl(var(--sidebar-fg)/0.5)]">{maskGSTIN(client.gstin)}</p>
        <span className={`status-badge mt-1 text-[10px] ${status === 'active' ? 'status-active' : status === 'expired' ? 'status-expired' : 'status-none'}`}>
          {status === 'active' ? 'Active' : status === 'expired' ? 'Expired' : 'No Session'}
        </span>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
          <button className="mt-1 rounded p-0.5 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-[hsl(var(--sidebar-muted))]">
            <MoreVertical className="h-4 w-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); }}>
            <Pencil className="mr-2 h-3.5 w-3.5" /> Edit
          </DropdownMenuItem>
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={(e) => { e.stopPropagation(); dispatch({ type: 'DELETE_CLIENT', payload: client.id }); }}
          >
            <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
