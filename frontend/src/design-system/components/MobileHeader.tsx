import type { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/cn";

export function MobileHeader({
  title,
  showBack = false,
  onBack,
  action,
  className,
}: {
  title?: ReactNode;
  showBack?: boolean;
  onBack?: () => void;
  action?: ReactNode;
  className?: string;
}) {
  const navigate = useNavigate();
  const handleBack = onBack ?? (() => navigate(-1));

  return (
    <header
      className={cn(
        "shrink-0 sticky top-0 z-10 bg-bg/95 backdrop-blur supports-[backdrop-filter]:bg-bg/80",
        "flex items-center gap-2 px-4 h-14",
        className,
      )}
    >
      {showBack ? (
        <button
          type="button"
          onClick={handleBack}
          aria-label="Back"
          className="-ml-1.5 p-1.5 rounded-full text-text hover:bg-surface-2 transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
      ) : null}
      <h1 className="flex-1 text-lg font-semibold tracking-tight truncate">
        {title}
      </h1>
      {action ? <div className="flex items-center gap-2">{action}</div> : null}
    </header>
  );
}
