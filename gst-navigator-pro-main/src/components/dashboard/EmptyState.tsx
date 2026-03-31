import { ReactNode } from 'react';
import { FileQuestion } from 'lucide-react';

interface EmptyProps {
  message?: string;
  onFetch?: () => void;
}

export function EmptyState({ message = 'No data — click Fetch to retrieve this section', onFetch }: EmptyProps) {
  return (
    <div className="empty-state">
      <FileQuestion className="h-8 w-8 text-muted-foreground/40 mb-2" />
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
        {errorCode && <span className="font-mono mr-2">[{errorCode}]</span>}
        {message || 'An error occurred'}
      </p>
    </div>
  );
}
