import * as React from 'react';
import { cn } from '@/lib/utils';

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Height of the scroll area */
  className?: string;
}

export function ScrollArea({ className, children, ...props }: ScrollAreaProps) {
  return (
    <div
      className={cn('relative overflow-auto rounded-md border', className)}
      {...props}
    >
      {children}
    </div>
  );
}

// Optional ScrollBar component placeholder (no custom styling needed for functionality)
export function ScrollBar({ orientation = 'vertical' }: { orientation?: 'vertical' | 'horizontal' }) {
  // This is a no-op placeholder to satisfy imports; native scrollbars are used.
  return null;
}
