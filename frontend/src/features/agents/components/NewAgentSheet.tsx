import { useState } from "react";
import { ChevronDown, ImagePlus } from "lucide-react";
import { useCreateAgent } from "@/api/endpoints/agents";
import { useSettingsStore } from "@/store/settings";
import { ALL_CAPABILITY_TAGS } from "./ProfileForm";
import { cn } from "@/lib/cn";

const MAX_TAGS = 10;
const AVATAR_MAX_DIM = 512; // 축소 후 긴 변 최대 px
const isImageFile = (file: File): boolean => file.type === "" || file.type.startsWith("image/");

/**
 * 선택한 이미지를 캔버스로 축소하고 JPEG data URL 로 변환한다.
 * - iPhone 사진(수 MB HEIC)을 2MB 이하로 줄여 용량 문제를 없앤다.
 * - HEIC → JPEG 변환으로 REQ-0102 포맷(JPEG/PNG)도 충족한다.
 * - iOS Safari 는 HEIC 를 디코딩할 수 있어 Image 로딩 → 캔버스 그리기가 동작한다.
 */
function resizeImageToJpegDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const scale = Math.min(1, AVATAR_MAX_DIM / Math.max(img.width, img.height));
      const w = Math.max(1, Math.round(img.width * scale));
      const h = Math.max(1, Math.round(img.height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("no-2d-context"));
        return;
      }
      ctx.drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("image-load-failed"));
    };
    img.src = url;
  });
}

/**
 * Empty "edit profile" form rendered INLINE in the Profile tab (not an overlay)
 * when "Add profile" is chosen from the agent dropdown. A blank
 * ProfileEditCard-style form for creating a new agent.
 */
export function NewAgentForm({ onClose }: { onClose: () => void }) {
  const create = useCreateAgent();
  const apiKeys = useSettingsStore((s) => s.apiKeys);
  const [localKeys, setLocalKeys] = useState<string[]>([]);
  const keyNames = [...apiKeys.map((k) => k.name), ...localKeys];
  const [name, setName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [bio, setBio] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [keyName, setKeyName] = useState("");
  const [addKeyOpen, setAddKeyOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeySecret, setNewKeySecret] = useState("");
  const [casual, setCasual] = useState(50);
  const [detail, setDetail] = useState(50);
  const [bold, setBold] = useState(50);
  const [autoMatch, setAutoMatch] = useState(false);
  const [task, setTask] = useState("");

  const onAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      setAvatarUrl(null);
      setAvatarError(null);
      return;
    }
    if (!isImageFile(file)) {
      setAvatarError("Use an image file.");
      return;
    }
    setAvatarError(null);
    resizeImageToJpegDataUrl(file)
      .then((dataUrl) => setAvatarUrl(dataUrl))
      .catch(() => setAvatarError("Couldn't load that image. Try another."));
  };

  const toggleTag = (tag: string) => {
    setTags((prev) => {
      if (prev.includes(tag)) return prev.filter((t) => t !== tag);
      if (prev.length >= MAX_TAGS) return prev;
      return [...prev, tag];
    });
  };

  const addKey = () => {
    const nm = newKeyName.trim();
    if (!nm || !newKeySecret.trim()) return;
    if (!keyNames.includes(nm)) setLocalKeys((prev) => [...prev, nm]);
    setKeyName(nm);
    setNewKeyName("");
    setNewKeySecret("");
    setAddKeyOpen(false);
  };

  const submit = () => {
    if (!name.trim() || create.isPending) return;
    create.mutate(
      {
        displayName: name.trim(),
        bio,
        capabilityTags: tags,
        styleCasual: casual,
        styleDetail: detail,
        styleBold: bold,
        interactionStyle: { verbosity: "concise", formality: "casual" },
        availability: { timezone: "UTC", windows: [] },
      },
      { onSuccess: () => onClose() },
    );
  };

  return (
        <div className="rounded-[24px] bg-bg shadow-float p-4 flex flex-col gap-3">
          <h2 className="text-h3 font-semibold text-text">New profile</h2>

          {/* Avatar — tap to open the native picker (JPEG/PNG, ≤2MB); shows a preview. */}
          <label className="relative h-[200px] w-full rounded-[24px] bg-surface-2 grid place-items-center text-text-subtle cursor-pointer overflow-hidden">
            {avatarUrl ? (
              <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <span className="grid place-items-center w-14 h-14 rounded-full bg-bg shadow-float text-text-muted active:scale-95 transition-transform">
                <ImagePlus className="w-6 h-6" strokeWidth={1.75} />
              </span>
            )}
            <input
              type="file"
              accept="image/*"
              aria-label="Edit avatar image"
              className="absolute inset-0 opacity-0 cursor-pointer"
              onChange={onAvatarChange}
            />
          </label>
          {avatarError ? <p className="text-body2 text-danger">{avatarError}</p> : null}

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
                    selected
                      ? "bg-primary text-primary-fg"
                      : "bg-tag text-text-muted hover:text-text",
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

          <button
            type="button"
            onClick={submit}
            disabled={!name.trim() || create.isPending}
            className="w-full rounded-[12px] bg-primary py-3 text-body1 font-bold text-primary-fg disabled:opacity-60"
          >
            Add profile
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
