import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { useAgentProfile, useUpdateAgent } from "@/api/endpoints/agents";
import type { AgentId, AgentProfile } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TrustTag } from "@/design-system/components/TrustTag";
import { cn } from "@/lib/cn";

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
  const [adding, setAdding] = useState("");
  const [autoMatch, setAutoMatch] = useState(false);
  const [task, setTask] = useState("");
  const [casual, setCasual] = useState(profile.styleCasual ?? 50);
  const [detail, setDetail] = useState(profile.styleDetail ?? 50);
  const [bold, setBold] = useState(profile.styleBold ?? 50);

  // Re-seed when switching to a different agent.
  useEffect(() => {
    setBio(profile.bio);
    setTags(profile.capabilityTags);
    setCasual(profile.styleCasual ?? 50);
    setDetail(profile.styleDetail ?? 50);
    setBold(profile.styleBold ?? 50);
  }, [profile.agentId, profile.bio, profile.capabilityTags, profile.styleCasual, profile.styleDetail, profile.styleBold]);

  const addTag = () => {
    const v = adding.trim();
    if (v && !tags.includes(v)) setTags([...tags, v]);
    setAdding("");
  };

  const save = () =>
    update.mutate({ bio, capabilityTags: tags } as Parameters<typeof update.mutate>[0]);

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

      {/* Tags with remove (x) + add */}
      <div className="flex flex-wrap items-center gap-1">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-[8px] bg-tag pl-2 pr-1 py-1 text-caption font-semibold text-text-muted"
          >
            {tag}
            <button
              type="button"
              onClick={() => {
                setTags(tags.filter((x) => x !== tag));
                save();
              }}
              aria-label={`Remove ${tag}`}
              className="grid place-items-center rounded-full hover:text-danger"
            >
              <X className="w-3 h-3" strokeWidth={2.5} />
            </button>
          </span>
        ))}
        <input
          value={adding}
          onChange={(e) => setAdding(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
          onBlur={() => {
            addTag();
            save();
          }}
          placeholder="+ add"
          className="w-[64px] rounded-[8px] bg-bg shadow-inset px-2 py-1 text-caption text-text placeholder:text-text-subtle focus:outline-none"
        />
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
