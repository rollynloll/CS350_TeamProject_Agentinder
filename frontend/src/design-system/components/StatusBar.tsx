import { Wifi } from "lucide-react";

/**
 * Figma `iOS_topBar` (node 2025:919) — 59px status bar: time on the left,
 * cellular / wifi / battery glyphs on the right. Static mock chrome so the
 * phone frame matches the Figma vertical rhythm (header sits 16px below it).
 */
export function StatusBar() {
  return (
    <div className="shrink-0 h-[59px] flex items-end justify-between px-[30px] pb-3 text-text select-none">
      <span className="text-[15px] font-semibold tracking-tight tabular-nums">9:41</span>
      <div className="flex items-center gap-1.5">
        {/* Cellular */}
        <svg width="18" height="12" viewBox="0 0 18 12" fill="none" aria-hidden>
          <rect x="0" y="8" width="3" height="4" rx="1" fill="currentColor" />
          <rect x="5" y="5.5" width="3" height="6.5" rx="1" fill="currentColor" />
          <rect x="10" y="3" width="3" height="9" rx="1" fill="currentColor" />
          <rect x="15" y="0" width="3" height="12" rx="1" fill="currentColor" />
        </svg>
        <Wifi className="w-[17px] h-[17px]" strokeWidth={2.25} />
        {/* Battery */}
        <svg width="27" height="13" viewBox="0 0 27 13" fill="none" aria-hidden>
          <rect x="0.5" y="0.5" width="22" height="12" rx="3" stroke="currentColor" opacity="0.4" />
          <rect x="2" y="2" width="17" height="9" rx="1.5" fill="currentColor" />
          <rect x="24" y="4" width="1.5" height="5" rx="0.75" fill="currentColor" opacity="0.4" />
        </svg>
      </div>
    </div>
  );
}
