import * as Dialog from "@radix-ui/react-dialog";
import { Link } from "react-router-dom";
import { BellOff, History, Slash, UserCircle2, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

type Item = {
  icon: LucideIcon;
  label: string;
  to?: string;
  onClick?: () => void;
  danger?: boolean;
};

export function ConversationMenuSheet({
  open,
  onOpenChange,
  matchId,
  onViewProfile,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  partnerAgentId?: string;
  matchId?: string;
  onViewProfile?: () => void;
}) {
  const items: Item[] = [
    {
      icon: UserCircle2,
      label: "View partner profile",
      onClick: onViewProfile,
    },
    {
      icon: History,
      label: "View date history",
      to: matchId ? `/matches/${matchId}/history` : undefined,
    },
    {
      icon: BellOff,
      label: "Mute conversation",
      onClick: () => {
        console.info("[Conversation] mute toggled (mock)");
      },
    },
    { icon: Slash, label: "Block", danger: true, onClick: () => undefined },
  ];

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Overlay className="absolute inset-0 bg-black/50 z-40" />
      <Dialog.Content
        className={cn(
          "absolute top-0 right-0 bottom-0 z-50 w-[80%] max-w-[320px] bg-bg border-l border-border shadow-elevated focus:outline-none",
        )}
      >
          <div className="flex items-center justify-between gap-2 px-4 h-14 border-b border-border">
            <Dialog.Title className="text-h3 font-semibold">
              Conversation menu
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close menu"
                className="p-1.5 rounded-full text-text-muted hover:bg-surface-2"
              >
                <X className="w-5 h-5" />
              </button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">
            Conversation actions and links
          </Dialog.Description>
          <ul className="py-2">
            {items.map(({ icon: Icon, label, to, onClick, danger }) => {
              const body = (
                <span
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 text-body1 font-medium transition-colors",
                    danger ? "text-danger" : "text-text",
                    "hover:bg-surface-2",
                  )}
                >
                  <Icon className="w-5 h-5" strokeWidth={1.75} />
                  {label}
                </span>
              );

              return (
                <li key={label}>
                  {to ? (
                    <Link to={to} onClick={() => onOpenChange(false)}>
                      {body}
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        onClick?.();
                        onOpenChange(false);
                      }}
                      className="w-full text-left"
                    >
                      {body}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
      </Dialog.Content>
    </Dialog.Root>
  );
}
