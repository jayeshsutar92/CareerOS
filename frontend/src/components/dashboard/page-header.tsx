import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Breadcrumbs,
  type BreadcrumbItem,
} from "@/components/dashboard/breadcrumbs";

type PageHeaderProps = {
  title: string;
  description?: string;
  icon?: LucideIcon;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
  className?: string;
};

export function PageHeader({
  title,
  description,
  icon: Icon,
  breadcrumbs,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-500", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumbs items={breadcrumbs} />
      )}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="flex size-10 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04]">
              <Icon aria-hidden="true" className="size-5 text-white" />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-semibold text-white">{title}</h1>
            {description && (
              <p className="mt-0.5 text-sm text-zinc-400">{description}</p>
            )}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
