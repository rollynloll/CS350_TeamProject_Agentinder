import { forwardRef, useState, type PointerEvent } from "react";
import { Delete, Globe, Mic, Smile } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * Figma search keyboard (node 2051:1545): an iOS-style QWERTY keyboard pinned
 * to the bottom of the phone frame. Shown whenever a text field is focused.
 * Keys type into the currently-focused input/textarea.
 */
const ROWS = [
  ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
  ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
  ["z", "x", "c", "v", "b", "n", "m"],
];

function activeField(): HTMLInputElement | HTMLTextAreaElement | null {
  const el = document.activeElement as HTMLElement | null;
  if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) {
    const input = el as HTMLInputElement;
    if (input.type === "range") return null;
    return el as HTMLInputElement | HTMLTextAreaElement;
  }
  return null;
}

function setNativeValue(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  setter?.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}

export const Keyboard = forwardRef<HTMLDivElement>(function Keyboard(_props, ref) {
  const [shift, setShift] = useState(false);

  const type = (raw: string) => {
    const el = activeField();
    if (!el) return;
    const ch = shift ? raw.toUpperCase() : raw;
    const s = el.selectionStart ?? el.value.length;
    const e = el.selectionEnd ?? s;
    setNativeValue(el, el.value.slice(0, s) + ch + el.value.slice(e));
    const pos = s + ch.length;
    el.setSelectionRange?.(pos, pos);
    setShift(false);
  };

  const backspace = () => {
    const el = activeField();
    if (!el) return;
    const s = el.selectionStart ?? el.value.length;
    const e = el.selectionEnd ?? s;
    if (s === 0 && s === e) return;
    const from = s === e ? s - 1 : s;
    setNativeValue(el, el.value.slice(0, from) + el.value.slice(e));
    el.setSelectionRange?.(from, from);
  };

  const enter = () => activeField()?.blur();

  // Keep focus on the field — never let the key steal it.
  const hold = (e: PointerEvent) => e.preventDefault();

  const Key = ({
    children,
    onTap,
    className,
  }: {
    children: React.ReactNode;
    onTap: () => void;
    className?: string;
  }) => (
    <button
      type="button"
      onPointerDown={hold}
      onClick={onTap}
      className={cn(
        "grid place-items-center h-11 rounded-[6px] bg-surface-2 text-text shadow-card text-h3 active:bg-surface",
        className,
      )}
    >
      {children}
    </button>
  );

  return (
    <div
      ref={ref}
      className="absolute inset-x-0 bottom-0 z-50 bg-bg px-1.5 pt-2 pb-[max(0.4rem,env(safe-area-inset-bottom))] select-none shadow-elevated"
    >
      {/* Row 1 */}
      <div className="grid grid-cols-10 gap-1 mb-1.5">
        {ROWS[0].map((k) => (
          <Key key={k} onTap={() => type(k)}>
            {shift ? k.toUpperCase() : k}
          </Key>
        ))}
      </div>
      {/* Row 2 */}
      <div className="flex justify-center gap-1 mb-1.5">
        {ROWS[1].map((k) => (
          <Key key={k} onTap={() => type(k)} className="w-[9%] min-w-[30px] flex-1 max-w-[34px]">
            {shift ? k.toUpperCase() : k}
          </Key>
        ))}
      </div>
      {/* Row 3 */}
      <div className="flex gap-1 mb-1.5">
        <Key onTap={() => setShift((s) => !s)} className={cn("flex-[1.4]", shift && "!bg-primary !text-primary-fg")}>
          ⇧
        </Key>
        {ROWS[2].map((k) => (
          <Key key={k} onTap={() => type(k)} className="flex-1">
            {shift ? k.toUpperCase() : k}
          </Key>
        ))}
        <Key onTap={backspace} className="flex-[1.4]">
          <Delete className="w-5 h-5" strokeWidth={2} />
        </Key>
      </div>
      {/* Row 4 */}
      <div className="flex gap-1">
        <Key onTap={() => {}} className="flex-[1.4] !text-body2">
          ABC
        </Key>
        <Key onTap={() => type(" ")} className="flex-[5]">
          space
        </Key>
        <Key onTap={enter} className="flex-[1.8] !bg-primary !text-primary-fg">
          <Globe className="w-5 h-5" strokeWidth={2} />
        </Key>
      </div>
      {/* Bottom row */}
      <div className="flex items-center justify-between px-2 pt-2 text-text-muted">
        <Smile className="w-5 h-5" strokeWidth={2} />
        <Mic className="w-5 h-5" strokeWidth={2} />
      </div>
    </div>
  );
});
