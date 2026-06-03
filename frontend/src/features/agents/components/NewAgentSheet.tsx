import { useState } from "react";
import { ChevronDown, X } from "lucide-react";
import { useCreateAgent } from "@/api/endpoints/agents";
import { useSettings } from "@/api/endpoints/settings";

/**
 * Empty "edit profile" form rendered INLINE in the Profile tab (not an overlay)
 * when "Add profile" is chosen from the agent dropdown. A blank
 * ProfileEditCard-style form for creating a new agent.
 */
export function NewAgentForm({ onClose }: { onClose: () => void }) {
  const create = useCreateAgent();
  const { data: settings } = useSettings();
  const keyNames = settings?.apiKeys.map((k) => k.name) ?? [];
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [adding, setAdding] = useState("");
  const [keyName, setKeyName] = useState("");
  const [casual, setCasual] = useState(50);
  const [detail, setDetail] = useState(50);
  const [bold, setBold] = useState(50);
  const [autoMatch, setAutoMatch] = useState(false);
  const [task, setTask] = useState("");

  const addTag = () => {
    const v = adding.trim();
    if (v && !tags.includes(v)) setTags([...tags, v]);
    setAdding("");
  };

  const submit = () => {
    if (!name.trim() || create.isPending) return;
    create.mutate(
      {
        displayName: name.trim(),
        bio,
        capabilityTags: tags,
        interactionStyle: { verbosity: "concise", formality: "casual" },
        availability: { timezone: "UTC", windows: [] },
      },
      { onSuccess: () => onClose() },
    );
  };

  return (
        <div className="rounded-[24px] bg-bg shadow-float p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-h3 font-semibold text-text">New profile</h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="grid place-items-center w-8 h-8 rounded-full bg-surface-2 text-text-muted"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Avatar placeholder */}
          <div className="h-[200px] w-full rounded-[24px] bg-surface-2 grid place-items-center text-text-subtle text-body2">
            Avatar
          </div>

          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Agent name"
            className="w-full rounded-[12px] bg-bg shadow-inset px-3 py-2 text-h3 font-semibold text-text placeholder:text-text-subtle focus:outline-none"
          />

          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={3}
            placeholder="Describe your agent."
            className="w-full resize-none rounded-[12px] bg-bg shadow-inset px-3 py-2 text-body2 leading-[1.4] text-text placeholder:text-text-subtle focus:outline-none"
          />

          {/* Capability tags */}
          <p className="text-caption leading-[1.4] text-text-muted">Capability Tag</p>
          <div className="flex flex-wrap items-center gap-1">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-[8px] bg-tag pl-2 pr-1 py-1 text-caption font-semibold text-text-muted"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => setTags(tags.filter((x) => x !== tag))}
                  aria-label={`Remove ${tag}`}
                  className="grid place-items-center hover:text-danger"
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
              onBlur={addTag}
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

          {/* API Key — pick a key registered in Settings */}
          <div className="flex flex-col gap-2 pt-1">
            <p className="text-body1 font-semibold text-text">API Key</p>
            <div className="relative">
              <select
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                className="w-full appearance-none rounded-[12px] bg-bg shadow-inset px-3 py-2 pr-9 text-body2 text-text focus:outline-none"
              >
                <option value="">Select API key</option>
                {keyNames.map((nm) => (
                  <option key={nm} value={nm}>
                    {nm}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            </div>
          </div>

          <button
            type="button"
            onClick={submit}
            disabled={!name.trim() || create.isPending}
            className="w-full rounded-[12px] bg-primary py-3 text-body1 font-bold text-primary-fg disabled:opacity-60"
          >
            Create
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
      className={
        checked
          ? "relative h-7 w-[52px] shrink-0 rounded-full bg-primary transition-colors"
          : "relative h-7 w-[52px] shrink-0 rounded-full bg-bg shadow-inset transition-colors"
      }
    >
      <span
        className={
          checked
            ? "absolute top-1 left-1 h-5 w-5 rounded-full bg-surface shadow-float translate-x-[24px] transition-transform"
            : "absolute top-1 left-1 h-5 w-5 rounded-full bg-surface shadow-float translate-x-0 transition-transform"
        }
      />
    </button>
  );
}
