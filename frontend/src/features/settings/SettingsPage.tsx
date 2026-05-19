import { useTranslation } from "react-i18next";
import {
  Bell,
  ChevronRight,
  KeyRound,
  Shield,
  ShieldCheck,
  Sparkles,
  UserCog,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useSettings } from "@/api/endpoints/settings";
import { Button } from "@/design-system/components/Button";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { useAuth } from "@/store/auth";

type Row = { icon: LucideIcon; label: string; onClick?: () => void };
type Group = { title: string; rows: Row[] };

export function SettingsPage() {
  const { t } = useTranslation();
  const query = useSettings();
  const { logout } = useAuth();

  const groups: Group[] = [
    {
      title: "Category",
      rows: [
        { icon: UserCog, label: "Account" },
        { icon: KeyRound, label: "API Key Management" },
      ],
    },
    {
      title: "Category",
      rows: [
        { icon: Bell, label: "Notice" },
        { icon: Shield, label: "Privacy control" },
      ],
    },
    {
      title: "Category",
      rows: [
        { icon: ShieldCheck, label: "Global trust threshold" },
        { icon: Sparkles, label: "Auto-match rule" },
      ],
    },
  ];

  return (
    <>
      <MobileHeader title={t("settings.title")} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-4">
        <QueryBoundary query={query}>
          {() =>
            groups.map((group, idx) => (
              <section key={idx}>
                <div className="text-[11px] font-medium text-text-subtle mb-1 ml-1">
                  {group.title}
                </div>
                <div className="rounded-2xl bg-surface shadow-card overflow-hidden">
                  {group.rows.map((row, rIdx) => (
                    <SettingRow
                      key={row.label}
                      row={row}
                      showDivider={rIdx < group.rows.length - 1}
                    />
                  ))}
                </div>
              </section>
            ))
          }
        </QueryBoundary>

        <div className="pt-2">
          <Button
            variant="secondary"
            size="md"
            className="w-full"
            onClick={() => logout()}
          >
            Log out
          </Button>
        </div>
      </div>
    </>
  );
}

function SettingRow({ row, showDivider }: { row: Row; showDivider: boolean }) {
  const Icon = row.icon;
  return (
    <button
      type="button"
      onClick={row.onClick}
      className="w-full flex items-center gap-3 px-4 py-3.5 text-sm font-medium text-text hover:bg-surface-2 transition-colors"
      style={{
        boxShadow: showDivider ? "inset 0 -1px 0 var(--color-border)" : undefined,
      }}
    >
      <Icon className="w-5 h-5 text-text" strokeWidth={1.75} />
      <span className="flex-1 text-left">{row.label}</span>
      <ChevronRight className="w-4 h-4 text-text-subtle" />
    </button>
  );
}
