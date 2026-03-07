import { type LucideIcon, Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: LucideIcon;
}

export function EmptyState({
  title = "No data",
  description = "Nothing to display here yet.",
  icon: Icon = Inbox,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <Icon className="h-10 w-10 text-slate-300 dark:text-slate-600" />
      <div>
        <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{title}</p>
        <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{description}</p>
      </div>
    </div>
  );
}
