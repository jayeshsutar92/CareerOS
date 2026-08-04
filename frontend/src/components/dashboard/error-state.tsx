import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

type ErrorStateProps = {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
};

export function ErrorState({
  title = "Something went wrong",
  description = "There was an error loading the data. Please try again.",
  action,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-red-500/20 bg-red-500/5 px-6 py-12 text-center",
        className,
      )}
    >
      <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-red-500/10">
        <AlertTriangle aria-hidden="true" className="size-6 text-red-500" />
      </div>
      <h3 className="text-base font-medium text-red-400">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-red-400/80">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
