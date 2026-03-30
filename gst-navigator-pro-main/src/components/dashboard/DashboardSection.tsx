import { ReactNode } from 'react';
import { AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { formatTimestamp } from '@/lib/formatters';
import { Skeleton } from '@/components/ui/skeleton';

interface Props {
  id: string;
  title: string;
  lastUpdated?: string;
  loading?: boolean;
  children: ReactNode;
}

export function DashboardSection({ id, title, lastUpdated, loading, children }: Props) {
  return (
    <AccordionItem value={id} className="mb-3 overflow-hidden rounded-lg border">
      <AccordionTrigger className="px-4 py-3 hover:bg-muted/30 hover:no-underline">
        <div className="flex items-center gap-3 text-left">
          <span className="text-sm font-semibold">{title}</span>
          {lastUpdated && (
            <span className="text-[10px] font-normal text-muted-foreground">
              Updated: {formatTimestamp(lastUpdated)}
            </span>
          )}
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-4 pb-4">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-3/4" />
          </div>
        ) : children}
      </AccordionContent>
    </AccordionItem>
  );
}
