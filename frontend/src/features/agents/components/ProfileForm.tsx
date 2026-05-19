import { useState, type FormEvent } from "react";
import * as Slider from "@radix-ui/react-slider";
import { ChevronDown, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import type { AvailabilityWindow } from "@/api/types";

export const ALL_CAPABILITY_TAGS = [
  "Analyze",
  "Logic",
  "Research",
  "Fast",
  "Optimize",
  "Economy",
  "Plan",
  "Image",
  "Math",
  "Creative",
  "Schedule",
  "Graph",
  "Problem Solve",
] as const;

export const BASE_MODELS = [
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "claude-sonnet", label: "Claude Sonnet" },
  { value: "gemini-pro", label: "Gemini Pro" },
  { value: "ChatGPT-4", label: "ChatGPT-4" },
] as const;

export const WEEKDAYS: Array<AvailabilityWindow["day"]> = [
  "MON",
  "TUE",
  "WED",
  "THU",
  "FRI",
  "SAT",
  "SUN",
];

export type ProfileFormValues = {
  baseModel: string;
  apiKey: string;
  avatarUrl: string | null;
  displayName: string;
  description: string;
  capabilityTags: string[];
  styleCasual: number;
  styleDetail: number;
  styleBold: number;
  activeDays: Array<AvailabilityWindow["day"]>;
  activeStart: string;
  activeEnd: string;
};

export const DEFAULT_VALUES: ProfileFormValues = {
  baseModel: "",
  apiKey: "",
  avatarUrl: null,
  displayName: "",
  description: "",
  capabilityTags: [],
  styleCasual: 50,
  styleDetail: 50,
  styleBold: 50,
  activeDays: [],
  activeStart: "09:00",
  activeEnd: "18:00",
};

const MAX_NAME = 16;
const MAX_DESCRIPTION = 500;
const MAX_TAGS = 10;

export function ProfileForm({
  formId,
  defaultValues = DEFAULT_VALUES,
  mode,
  onSubmit,
}: {
  formId: string;
  mode: "create" | "edit";
  defaultValues?: ProfileFormValues;
  onSubmit: (values: ProfileFormValues) => void;
}) {
  const [values, setValues] = useState<ProfileFormValues>(defaultValues);

  const update = <K extends keyof ProfileFormValues>(
    key: K,
    value: ProfileFormValues[K],
  ) => setValues((prev) => ({ ...prev, [key]: value }));

  const toggleTag = (tag: string) => {
    setValues((prev) => {
      const has = prev.capabilityTags.includes(tag);
      if (has) {
        return {
          ...prev,
          capabilityTags: prev.capabilityTags.filter((t) => t !== tag),
        };
      }
      if (prev.capabilityTags.length >= MAX_TAGS) return prev;
      return { ...prev, capabilityTags: [...prev.capabilityTags, tag] };
    });
  };

  const toggleDay = (day: AvailabilityWindow["day"]) => {
    setValues((prev) => ({
      ...prev,
      activeDays: prev.activeDays.includes(day)
        ? prev.activeDays.filter((d) => d !== day)
        : [...prev.activeDays, day],
    }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!values.displayName.trim()) return;
    if (!values.baseModel) return;
    onSubmit(values);
  };

  return (
    <form
      id={formId}
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 px-4 pb-6 pt-2"
    >
      <FormCard>
        <label className="flex items-center gap-2 text-sm">
          <ChevronDown className="w-4 h-4 text-primary" />
          <select
            value={values.baseModel}
            onChange={(e) => update("baseModel", e.target.value)}
            className="flex-1 bg-transparent focus:outline-none appearance-none cursor-pointer"
            required
          >
            <option value="" disabled>
              Select based model.
            </option>
            {BASE_MODELS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
      </FormCard>

      <FormCard>
        <input
          type="text"
          value={values.apiKey}
          onChange={(e) => update("apiKey", e.target.value)}
          placeholder={
            mode === "edit"
              ? defaultValues.apiKey || "API key"
              : "Enter API KEY. (Don't share with others)"
          }
          className="w-full bg-transparent text-sm focus:outline-none"
        />
      </FormCard>

      <AvatarUploader
        value={values.avatarUrl}
        onChange={(url) => update("avatarUrl", url)}
      />

      <FormCard>
        <input
          type="text"
          value={values.displayName}
          onChange={(e) => update("displayName", e.target.value.slice(0, MAX_NAME))}
          placeholder={`Enter agent name. (Max ${MAX_NAME} characters)`}
          maxLength={MAX_NAME}
          className="w-full bg-transparent text-sm focus:outline-none"
          required
        />
      </FormCard>

      <FormCard>
        <textarea
          value={values.description}
          onChange={(e) =>
            update("description", e.target.value.slice(0, MAX_DESCRIPTION))
          }
          rows={3}
          maxLength={MAX_DESCRIPTION}
          placeholder={`Enter agent description (Up to ${MAX_DESCRIPTION} characters)`}
          className="w-full bg-transparent text-sm focus:outline-none resize-none"
        />
      </FormCard>

      <FormCard>
        <div className="text-xs text-text-muted mb-2">
          Select up to {MAX_TAGS} capability tags
        </div>
        <div className="flex flex-wrap gap-1.5">
          {ALL_CAPABILITY_TAGS.map((tag) => {
            const selected = values.capabilityTags.includes(tag);
            return (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                className={cn(
                  "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium border transition-colors",
                  selected
                    ? "bg-surface text-text border-primary"
                    : "bg-surface-2 text-text-muted border-transparent hover:border-border",
                )}
              >
                {tag}
              </button>
            );
          })}
        </div>
      </FormCard>

      <FormCard>
        <div className="text-xs text-text-muted mb-3">
          Define the agent&apos;s conversation style
        </div>
        <StyleSlider
          label="Casual"
          value={values.styleCasual}
          onChange={(v) => update("styleCasual", v)}
        />
        <StyleSlider
          label="Detail"
          value={values.styleDetail}
          onChange={(v) => update("styleDetail", v)}
        />
        <StyleSlider
          label="Bold"
          value={values.styleBold}
          onChange={(v) => update("styleBold", v)}
        />
      </FormCard>

      <FormCard>
        <div className="text-xs text-text-muted mb-2">Active time</div>
        <div className="flex gap-1.5 mb-3">
          {WEEKDAYS.map((day) => {
            const selected = values.activeDays.includes(day);
            return (
              <button
                key={day}
                type="button"
                onClick={() => toggleDay(day)}
                aria-pressed={selected}
                className={cn(
                  "flex-1 rounded-full py-1.5 text-[11px] font-semibold transition-colors",
                  selected
                    ? "bg-primary text-primary-fg"
                    : "bg-surface-2 text-text-muted",
                )}
              >
                {day[0] + day.slice(1).toLowerCase()}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2 text-sm">
          <input
            type="time"
            value={values.activeStart}
            onChange={(e) => update("activeStart", e.target.value)}
            className="flex-1 rounded-lg bg-surface-2 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-primary"
            aria-label="Active time start"
          />
          <span className="text-text-subtle">~</span>
          <input
            type="time"
            value={values.activeEnd}
            onChange={(e) => update("activeEnd", e.target.value)}
            className="flex-1 rounded-lg bg-surface-2 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-primary"
            aria-label="Active time end"
          />
        </div>
      </FormCard>
    </form>
  );
}

function FormCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-surface shadow-card px-4 py-3">{children}</div>
  );
}

function AvatarUploader({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (url: string | null) => void;
}) {
  return (
    <label className="grid place-items-center rounded-xl bg-surface shadow-card aspect-square w-32 mx-0 cursor-pointer text-text-subtle hover:text-primary transition-colors relative overflow-hidden">
      {value ? (
        <img src={value} alt="Avatar" className="w-full h-full object-cover" />
      ) : (
        <div className="text-center">
          <ImageIcon className="w-6 h-6 mx-auto mb-1" strokeWidth={1.5} />
          <div className="text-xs">Add an avatar image</div>
        </div>
      )}
      <input
        type="file"
        accept="image/*"
        className="absolute inset-0 opacity-0 cursor-pointer"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (!file) {
            onChange(null);
            return;
          }
          const reader = new FileReader();
          reader.onload = () => onChange(reader.result as string);
          reader.readAsDataURL(file);
        }}
      />
    </label>
  );
}

function StyleSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="py-2">
      <div className="text-[11px] text-text-muted mb-1">{label}</div>
      <Slider.Root
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={0}
        max={100}
        step={1}
        className="relative flex items-center select-none touch-none w-full h-5"
      >
        <Slider.Track className="bg-surface-2 relative grow rounded-full h-1.5">
          <Slider.Range className="absolute bg-primary rounded-full h-full" />
        </Slider.Track>
        <Slider.Thumb
          aria-label={label}
          className="block w-4 h-4 bg-primary rounded-full shadow-card focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </Slider.Root>
    </div>
  );
}
