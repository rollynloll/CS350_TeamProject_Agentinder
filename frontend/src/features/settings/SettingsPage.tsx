import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useSettings, useUpdateSettings } from "@/api/endpoints/settings";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { cn } from "@/lib/cn";
import type { SettingsResponse } from "@/api/types";

/**
 * Figma Settings (node 2064:1567): one scrolling page of neumorphic section
 * cards — Account, Auto Matching, Notification, API Key — each with inline
 * rows, 3D switches, sliders, and the emergency Kill Switch.
 */
export function SettingsPage() {
  const { t } = useTranslation();
  const query = useSettings();

  return (
    <>
      <MobileHeader showBack title={t("settings.title")} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-8 space-y-4">
        <QueryBoundary query={query}>{(data) => <Body data={data} />}</QueryBoundary>
      </div>
    </>
  );
}

function Body({ data }: { data: SettingsResponse }) {
  const update = useUpdateSettings();
  const [mfa, setMfa] = useState(false);
  const [hideFromFeed, setHideFromFeed] = useState(false);
  // Local mirrors so toggles/sliders react instantly (the mock mutation does
  // not echo state back synchronously).
  const [n, setN] = useState(data.notifications);
  const auto = data.preferences.autoMatchRules;
  const [autoEnabled, setAutoEnabled] = useState(auto.enabled);
  const [trustFilter, setTrustFilter] = useState(Math.round(auto.minTrust * 100));
  const [autoLimit, setAutoLimit] = useState(2);

  const toggleNotif = (key: keyof SettingsResponse["notifications"], v: boolean) => {
    setN((prev) => ({ ...prev, [key]: v }));
    update.mutate({ notifications: { [key]: v } });
  };

  // API keys: left = key name, right = its (masked) API key.
  const [keys, setKeys] = useState(() =>
    data.apiKeys.map((k) => ({ name: k.name, masked: "sk-••••••••••••" })),
  );
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newKey, setNewKey] = useState("");
  const addKey = () => {
    if (!newName.trim() || !newKey.trim()) return;
    setKeys((prev) => [...prev, { name: newName.trim(), masked: maskKey(newKey.trim()) }]);
    setNewName("");
    setNewKey("");
    setAddOpen(false);
  };

  return (
    <>
      {/* Account */}
      <Section title="Account">
        <SubGroup label="Profile">
          <Row label="Email" value={data.account.email} />
          <Row label="MFA">
            <Switch checked={mfa} onChange={setMfa} />
          </Row>
        </SubGroup>
        <Divider />
        <SubGroup label="Connected accounts">
          <Row label="Google" value="googleID" muted />
          <Row label="GitHub" value="gitHubID" muted />
          <Row label="MS" value="MSID" muted />
        </SubGroup>
        <Divider />
        <Row label="Export Data">
          <GhostButton>Export</GhostButton>
        </Row>
        <Divider />
        <Row label="Delete Account">
          <GhostButton danger>Delete</GhostButton>
        </Row>
      </Section>

      {/* Auto Matching */}
      <Section title="Auto Matching">
        <SubGroup label="Policy">
          <Row label="Auto">
            <Switch
              checked={autoEnabled}
              onChange={(v) => {
                setAutoEnabled(v);
                update.mutate({ preferences: { autoMatchRules: { ...auto, enabled: v } } });
              }}
            />
          </Row>
          <SliderRow label="Trust Filter" value={trustFilter} onChange={setTrustFilter} />
        </SubGroup>
        <Divider />
        <SubGroup label="Limitation">
          <Row label="Weekly Date Limit">
            <Stepper value={20} />
          </Row>
          <SliderRow
            label="Auto Match Limit"
            value={autoLimit}
            max={10}
            onChange={setAutoLimit}
          />
        </SubGroup>
      </Section>

      {/* Notification */}
      <Section title="Notification">
        <Row label="New Match">
          <Switch checked={n.matchAlerts} onChange={(v) => toggleNotif("matchAlerts", v)} />
        </Row>
        <Row label="Date Done">
          <Switch checked={n.dateReminders} onChange={(v) => toggleNotif("dateReminders", v)} />
        </Row>
        <Row label="Trust Score Change">
          <Switch checked={n.weeklyDigest} onChange={(v) => toggleNotif("weeklyDigest", v)} />
        </Row>
        <Row label="Relationship Change">
          <Switch
            checked={n.messagePreview}
            onChange={(v) => toggleNotif("messagePreview", v)}
          />
        </Row>
      </Section>

      {/* API Key */}
      <Section title="API Key">
        <SubGroup label="KEY">
          {keys.length === 0 ? (
            <Row label="No keys yet" value="" muted />
          ) : (
            keys.map((k) => <Row key={k.name} label={k.name} value={k.masked} muted />)
          )}
          {addOpen ? (
            <div className="flex flex-col gap-2 pt-1">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Key name (e.g. GPT-agent)"
                className="w-full rounded-[8px] bg-bg shadow-inset px-3 py-2 text-body2 text-text placeholder:text-text-subtle focus:outline-none"
              />
              <input
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="API key (e.g. sk-...)"
                className="w-full rounded-[8px] bg-bg shadow-inset px-3 py-2 text-body2 text-text placeholder:text-text-subtle focus:outline-none"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAddOpen(false)}
                  className="rounded-[8px] bg-bg shadow-inset px-3 py-1 text-body2 font-semibold text-text-muted"
                >
                  Cancel
                </button>
                <GhostButton onClick={addKey}>Add</GhostButton>
              </div>
            </div>
          ) : (
            <div className="flex justify-end pt-1">
              <GhostButton onClick={() => setAddOpen(true)}>Add KEY</GhostButton>
            </div>
          )}
        </SubGroup>
        <Divider />
        <Row label="Regenerate Credentials">
          <GhostButton>Generate</GhostButton>
        </Row>
        <Divider />
        <SubGroup label="Emergency Controls">
          <Row label="Hide from Feed">
            <Switch checked={hideFromFeed} onChange={setHideFromFeed} />
          </Row>
          <Row label="Kill Switch">
            <button
              type="button"
              className="rounded-[8px] bg-danger px-3 py-1 text-caption font-bold text-white"
            >
              Stop ALL
            </button>
          </Row>
        </SubGroup>
      </Section>
    </>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-[12px] bg-bg shadow-float px-3 py-3 space-y-3">
      <h2 className="text-h3 font-semibold text-text">{title}</h2>
      {children}
    </section>
  );
}

function SubGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <p className="text-body1 font-semibold text-text">{label}</p>
      <div className="space-y-2 pl-1">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
  muted,
  children,
}: {
  label: string;
  value?: string;
  muted?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 min-h-[28px]">
      <span className="text-body1 text-text">{label}</span>
      {value !== undefined ? (
        <span className={cn("text-body1 truncate", muted ? "text-text-muted" : "text-text")}>
          {value}
        </span>
      ) : null}
      {children}
    </div>
  );
}

function Divider() {
  return <div className="h-px bg-border/70 my-1" />;
}

function Switch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-7 w-[52px] shrink-0 rounded-full transition-colors",
        checked ? "bg-primary" : "bg-bg shadow-inset",
      )}
    >
      <span
        className={cn(
          "absolute top-1 left-1 h-5 w-5 rounded-full bg-surface shadow-float transition-transform",
          checked ? "translate-x-[24px]" : "translate-x-0",
        )}
      />
    </button>
  );
}

function SliderRow({
  label,
  value,
  max = 100,
  onChange,
}: {
  label: string;
  value: number;
  max?: number;
  onChange?: (v: number) => void;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="space-y-2">
      <p className="text-body1 text-text">{label}</p>
      <div className="flex items-center gap-4">
        <div className="relative flex-1 h-4 flex items-center">
          <div className="absolute inset-x-0 h-1 rounded-full bg-bg shadow-inset" />
          <div
            className="absolute left-0 h-1 rounded-full bg-primary"
            style={{ width: `${pct}%` }}
          />
          <span
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-4 w-4 rounded-full bg-primary-light shadow-float pointer-events-none"
            style={{ left: `${pct}%` }}
          />
          <input
            type="range"
            min={0}
            max={max}
            value={value}
            onChange={(e) => onChange?.(Number(e.target.value))}
            aria-label={label}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>
        <span className="min-w-[30px] text-right text-h2 font-bold text-primary tabular-nums">
          {value}
        </span>
      </div>
    </div>
  );
}

function Stepper({ value }: { value: number }) {
  return (
    <span className="inline-flex items-center justify-center min-w-[54px] rounded-[8px] bg-bg shadow-inset px-3 py-1 text-body1 font-semibold text-text tabular-nums">
      {value}
    </span>
  );
}

function GhostButton({
  children,
  danger,
  onClick,
}: {
  children: ReactNode;
  danger?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-[8px] px-3 py-1 text-body2 font-semibold",
        danger ? "bg-danger/15 text-danger" : "bg-primary-light text-text",
      )}
    >
      {children}
    </button>
  );
}

function maskKey(key: string): string {
  const head = key.slice(0, 4);
  return `${head}${"•".repeat(Math.max(6, Math.min(12, key.length - 4)))}`;
}
