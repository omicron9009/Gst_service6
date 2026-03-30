import { FileQuestion } from 'lucide-react';

interface EmptyProps {
  message?: string;
  onFetch?: () => void;
}

export function EmptyState({ message = 'No data found for the selected period. Use Fetch to load this section.' }: EmptyProps) {
  return (
    <div className="empty-state">
      <FileQuestion className="mb-2 h-8 w-8 text-muted-foreground/40" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

interface ErrorProps {
  errorCode?: string;
  message?: string;
}

export function ErrorState({ errorCode, message }: ErrorProps) {
  return (
    <div className="error-state">
      <p className="text-sm font-medium text-destructive">
        {errorCode && <span className="mr-2 font-mono">[{errorCode}]</span>}
        {message || 'An error occurred.'}
      </p>
    </div>
  );
}
