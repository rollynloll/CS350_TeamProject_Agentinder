import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useAgentProfile, useUpdateAgent } from "@/api/endpoints/agents";
import { useSettingsStore } from "@/store/settings";
import type { AgentId, AgentProfile } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TrustTag } from "@/design-system/components/TrustTag";
import { ALL_CAPABILITY_TAGS } from "./ProfileForm";
import { cn } from "@/lib/cn";

const MAX_TAGS = 10;

/**
 * Figma 프로필-편집 card (node 2052:3221): the active agent's editable profile —
 * avatar, name + TrustTag, editable bio, capability tags with remove (x) + add,
 * Interaction Style sliders, and an Auto-match toggle with a task description.
 */
export function ProfileEditCard({ agentId }: { agentId: AgentId }) {
  const query = useAgentProfile(agentId);
  return <QueryBoundary query={query}>{(profile) => <Editor profile={profile} />}</QueryBoundary>;
}

function Editor({ profile }: { profile: AgentProfile }) {
  const update = useUpdateAgent(profile.agentId);
  const [bio, setBio] = useState(profile.bio);
  const [tags, setTags] = useState<string[]>(profile.capabilityTags);
  const [autoMatch, setAutoMatch] = useState(false);
  const [task, setTask] = useState("");
  const [casual, setCasual] = useState(profile.styleCasual ?? 50);
  const [detail, setDetail] = useState(profile.styleDetail ?? 50);
  const [bold, setBold] = useState(profile.styleBold ?? 50);

  // API Key — pick a key registered in Settings (same UX as the New profile form).
  const apiKeys = useSettingsStore((s) => s.apiKeys);
  const [localKeys, setLocalKeys] = useState<string[]>([]);
  const keyNames = [...apiKeys.map((k) => k.name), ...localKeys];
  const [keyName, setKeyName] = useState("");
  const [addKeyOpen, setAddKeyOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeySecret, setNewKeySecret] = useState("");

  const addKey = () => {
    const nm = newKeyName.trim();
    if (!nm || !newKeySecret.trim()) return;
    if (!keyNames.includes(nm)) setLocalKeys((prev) => [...prev, nm]);
    setKeyName(nm);
    setNewKeyName("");
    setNewKeySecret("");
    setAddKeyOpen(false);
  };

  // Re-seed when switching to a different agent.
  useEffect(() => {
    setBio(profile.bio);
    setTags(profile.capabilityTags);
    setCasual(profile.styleCasual ?? 50);
    setDetail(profile.styleDetail ?? 50);
    setBold(profile.styleBold ?? 50);
    setAutoMatch(profile.autoMatch ?? false);
    setTask(profile.taskDescription ?? "");
  }, [
    profile.agentId,
    profile.bio,
    profile.capabilityTags,
    profile.styleCasual,
    profile.styleDetail,
    profile.styleBold,
    profile.autoMatch,
    profile.taskDescription,
  ]);

  const save = () =>
    update.mutate({ bio, capabilityTags: tags, autoMatch, taskDescription: task } as Parameters<
      typeof update.mutate
    >[0]);

  const toggleTag = (tag: string) => {
    setTags((prev) => {
      const next = prev.includes(tag)
        ? prev.filter((t) => t !== tag)
        : prev.length >= MAX_TAGS
          ? prev
          : [...prev, tag];
      update.mutate({ bio, capabilityTags: next } as Parameters<typeof update.mutate>[0]);
      return next;
    });
  };

  return (
    <div className="rounded-[24px] bg-bg shadow-float p-4 flex flex-col gap-3">
      {/* Avatar */}
      <div className="relative h-[300px] w-full overflow-hidden rounded-t-[24px] bg-surface-2">
        <Avatar
          src={profile.avatarUrl}
          name={profile.displayName}
          size="xl"
          className="!w-full !h-full !rounded-t-[24px] !rounded-b-none !text-4xl"
        />
      </div>

      {/* Name + TrustTag */}
      <div className="flex items-center gap-2">
        <h2 className="flex-1 min-w-0 truncate text-h3 font-semibold text-text">
          {profile.displayName}
        </h2>
        <TrustTag score={profile.trustScore} showChevron={false} />
      </div>

      {/* Editable bio */}
      <textarea
        value={bio}
        onChange={(e) => setBio(e.target.value)}
        onBlur={save}
        rows={3}
        className="w-full resize-none rounded-[12px] bg-bg shadow-inset px-3 py-2 text-body2 leading-[1.4] text-text-muted focus:outline-none focus:text-text"
      />

      {/* Capability tags — pick from the system-defined list, up to MAX_TAGS. */}
      <div className="flex items-center justify-between">
        <p className="text-caption leading-[1.4] text-text-muted">Capability Tag</p>
        <span className="text-caption text-text-subtle tabular-nums">
          {tags.length}/{MAX_TAGS}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-1">
        {ALL_CAPABILITY_TAGS.map((tag) => {
          const selected = tags.includes(tag);
          const disabled = !selected && tags.length >= MAX_TAGS;
          return (
            <button
              key={tag}
              type="button"
              onClick={() => toggleTag(tag)}
              disabled={disabled}
              aria-pressed={selected}
              className={cn(
                "rounded-[8px] px-2 py-1 text-caption font-semibold transition-colors",
                selected ? "bg-primary text-primary-fg" : "bg-tag text-text-muted hover:text-text",
                disabled && "opacity-40 cursor-not-allowed",
              )}
            >
              {tag}
            </button>
          );
        })}
      </div>

      {/* Interaction Style */}
      <div className="flex flex-col gap-2 pt-1">
        <p className="text-caption text-text-muted">Interaction Style</p>
        <StyleSlider left="Formal" right="Casual" value={casual} onChange={setCasual} />
        <StyleSlider left="Verbose" right="Concise" value={detail} onChange={setDetail} />
        <StyleSlider left="Cautious" right="Bold" value={bold} onChange={setBold} />
      </div>

      {/* Auto-match */}
      <div className="flex flex-col gap-2 pt-1">
        <div className="flex items-center justify-between">
          <span className="text-body1 font-semibold text-text">Auto-match</span>
          <Switch checked={autoMatch} onChange={setAutoMatch} />
        </div>
        <textarea
          value={task}
          onChange={(e) => setTask(e.target.value)}
          rows={3}
          placeholder="Describe your task."
          className="w-full resize-none rounded-[12px] bg-bg shadow-inset px-3 py-2 text-body2 leading-[1.4] text-text placeholder:text-text-subtle focus:outline-none"
        />
      </div>

      {/* API Key — pick a key registered in Settings */}
      <div className="flex flex-col gap-2 pt-1">
        <p className="text-body1 font-semibold text-text">API Key</p>
        <div className="relative">
          <select
            value={keyName}
            onChange={(e) => {
              if (e.target.value === "__add__") {
                setAddKeyOpen(true);
                return;
              }
              setKeyName(e.target.value);
            }}
            className="w-full appearance-none rounded-[12px] bg-bg shadow-inset px-3 py-2 pr-9 text-body2 text-text focus:outline-none"
          >
            <option value="">Select API key</option>
            {keyNames.map((nm) => (
              <option key={nm} value={nm}>
                {nm}
              </option>
            ))}
            <option value="__add__">+ Add key</option>
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        </div>
        {addKeyOpen ? (
          <div className="flex flex-col gap-2">
            <input
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g. GPT-agent)"
              className="w-full rounded-[8px] bg-bg shadow-inset px-3 py-2 text-body2 text-text placeholder:text-text-subtle focus:outline-none"
            />
            <input
              value={newKeySecret}
              onChange={(e) => setNewKeySecret(e.target.value)}
              placeholder="API key (e.g. sk-...)"
              className="w-full rounded-[8px] bg-bg shadow-inset px-3 py-2 text-body2 text-text placeholder:text-text-subtle focus:outline-none"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setAddKeyOpen(false);
                  setNewKeyName("");
                  setNewKeySecret("");
                }}
                className="rounded-[8px] bg-bg shadow-inset px-3 py-1 text-body2 font-semibold text-text-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={addKey}
                className="rounded-[8px] bg-primary-light px-3 py-1 text-body2 font-semibold text-text"
              >
                Add
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {/* Save */}
      <button
        type="button"
        onClick={save}
        disabled={update.isPending}
        className="w-full rounded-[12px] bg-primary py-3 text-body1 font-bold text-primary-fg disabled:opacity-60"
      >
        {update.isPending ? "Saving…" : "Save"}
      </button>
    </div>
  );
}

function StyleSlider({
  left,
  right,
  value,
  onChange,
}: {
  left: string;
  right: string;
  value: number;
  onChange: (v: number) => void;
}) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-caption text-text-muted">
        <span>{left}</span>
        <span>{right}</span>
      </div>
      <div className="relative h-4 flex items-center">
        <div className="absolute inset-x-0 h-1 rounded-full bg-text-muted/20" />
        <div className="absolute left-0 h-1 rounded-full bg-primary" style={{ width: `${pct}%` }} />
        <span
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-4 w-4 rounded-full bg-primary-light shadow-float pointer-events-none"
          style={{ left: `${pct}%` }}
        />
        <input
          type="range"
          min={0}
          max={100}
          value={pct}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={`${left} to ${right}`}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
    </div>
  );
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
