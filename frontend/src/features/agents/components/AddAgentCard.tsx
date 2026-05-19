import { Link } from "react-router-dom";
import { Plus } from "lucide-react";

export function AddAgentCard() {
  return (
    <Link
      to="/agents/new"
      aria-label="Add new agent"
      className="grid place-items-center rounded-2xl border-2 border-dashed border-border bg-surface text-text-subtle hover:text-primary hover:border-primary transition-colors h-32"
    >
      <Plus className="w-8 h-8" strokeWidth={1.5} />
    </Link>
  );
}
