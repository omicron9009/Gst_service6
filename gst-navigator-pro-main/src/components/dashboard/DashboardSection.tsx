import { ReactNode } from 'react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
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
    <AccordionItem value={id} className="border rounded-lg mb-3 overflow-hidden">
      <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-muted/30">
        <div className="flex items-center gap-3 text-left">
          <span className="text-sm font-semibold">{title}</span>
          {lastUpdated && (
            <span className="text-[10px] text-muted-foreground font-normal">
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
