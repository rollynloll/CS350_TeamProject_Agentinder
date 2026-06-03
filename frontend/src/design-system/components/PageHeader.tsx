import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 pb-4 border-b border-border mb-6">
      <div>
        <h1 className="text-h2 font-bold tracking-tight">{title}</h1>
        {description ? (
          <p className="text-body1 text-text-muted mt-1">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
