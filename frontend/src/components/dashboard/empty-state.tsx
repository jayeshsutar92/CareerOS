import { Loader2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
};

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-white/10 px-6 py-16 text-center",
        className,
      )}
    >
      {Icon && (
        <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-white/[0.04]">
          <Icon aria-hidden="true" className="size-6 text-zinc-500" />
        </div>
      )}
      <h3 className="text-base font-medium text-white">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-zinc-500">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function PageLoader({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-[40vh] items-center justify-center",
        className,
      )}
    >
      <Loader2 className="size-6 animate-spin text-zinc-500" />
    </div>
  );
}
