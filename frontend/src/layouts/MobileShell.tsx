import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { StatusBar } from "@/design-system/components/StatusBar";
import { Keyboard } from "@/design-system/components/Keyboard";
import { KeyboardContext } from "@/design-system/components/keyboard-context";

function isTextField(el: EventTarget | null): boolean {
  const node = el as HTMLElement | null;
  if (!node) return false;
  if (node.tagName === "TEXTAREA") return true;
  if (node.tagName === "INPUT") return (node as HTMLInputElement).type !== "range";
  return false;
}

/**
 * Centers the app inside a phone-shaped canvas. On mobile the canvas fills the
 * viewport height; on desktop it's a 393x852 frame in the center. The Figma
 * iOS status bar pins to the top; children (per-screen header + scroll body +
 * BottomNav) stack below, and the inner box clips overflow so only the middle
 * scrolls. A Figma-style keyboard slides up whenever a text field is focused.
 */
export function MobileShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const [keyboard, setKeyboard] = useState(false);
  const [kbHeight, setKbHeight] = useState(0);
  const kbRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    setKbHeight(keyboard && kbRef.current ? kbRef.current.offsetHeight : 0);
  }, [keyboard]);

  // 키보드가 펼쳐진 직후, 포커스된 필드를 시야 중앙으로 끌어올린다. 브라우저
  // 기본 스크롤은 키보드가 자리잡기 전에 일어나 가려진 상태로 끝나기 쉽다.
  useEffect(() => {
    if (!keyboard || kbHeight === 0) return;
    const active = document.activeElement as HTMLElement | null;
    if (active && isTextField(active)) {
      active.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [keyboard, kbHeight]);

  useEffect(() => {
    const onFocusIn = (e: FocusEvent) => {
      if (isTextField(e.target)) setKeyboard(true);
    };
    const onFocusOut = () => {
      // Defer so clicking a key (which blurs then re-focuses) doesn't flicker.
      window.setTimeout(() => setKeyboard(isTextField(document.activeElement)), 0);
    };
    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("focusout", onFocusOut);
    return () => {
      document.removeEventListener("focusin", onFocusIn);
      document.removeEventListener("focusout", onFocusOut);
    };
  }, []);

  return (
    <div className="flex-1 min-h-0 self-stretch md:bg-surface-2/40 md:py-6 md:px-4 flex justify-center overflow-hidden">
      <div
        className={cn(
          "relative w-full h-full flex flex-col bg-bg overflow-hidden",
          "md:w-[393px] md:h-[852px] md:max-h-[calc(100dvh-3rem)] md:rounded-[2rem] md:shadow-elevated md:border md:border-border",
          className,
        )}
      >
        <KeyboardContext.Provider value={{ open: keyboard, height: kbHeight }}>
          <StatusBar />
          {children}
          {keyboard ? <Keyboard ref={kbRef} /> : null}
        </KeyboardContext.Provider>
      </div>
    </div>
  );
}
