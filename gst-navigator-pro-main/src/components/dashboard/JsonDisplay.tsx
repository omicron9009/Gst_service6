import { Copy, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface Props {
  data: any;
  title?: string;
  collapsible?: boolean;
  maxHeight?: string;
  className?: string;
}

export function JsonDisplay({
  data,
  title,
  collapsible = true,
  maxHeight = '300px',
  className = '',
}: Props) {
  const [collapsed, setCollapsed] = useState(collapsible);
  const [copied, setCopied] = useState(false);

  const jsonStr = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`border rounded-lg overflow-hidden bg-muted/30 ${className}`}>
      {(title || collapsible) && (
        <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/50">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {collapsible && (
              <button
                onClick={() => setCollapsed(!collapsed)}
                className="flex-shrink-0 hover:bg-muted p-0.5 rounded"
              >
                {collapsed ? (
                  <ChevronRight className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>
            )}
            {title && <span className="text-xs font-semibold text-muted-foreground truncate">{title}</span>}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 flex-shrink-0"
            onClick={handleCopy}
            title={copied ? 'Copied!' : 'Copy to clipboard'}
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {!collapsed && (
        <div style={{ maxHeight, overflowY: 'auto' }} className="w-full">
          <pre className="text-xs bg-background p-3 rounded-b m-0 font-mono text-foreground whitespace-pre-wrap break-words">
            {jsonStr}
          </pre>
        </div>
      )}
    </div>
  );
}

export default JsonDisplay;
