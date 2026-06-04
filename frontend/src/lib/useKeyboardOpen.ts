import { useEffect, useState } from "react";

function isTextField(el: EventTarget | null): boolean {
  const node = el as HTMLElement | null;
  if (!node) return false;
  if (node.tagName === "TEXTAREA") return true;
  if (node.tagName === "INPUT") return (node as HTMLInputElement).type !== "range";
  return node.isContentEditable;
}

/**
 * True while a text field is focused (≈ the on-screen keyboard is up). Driven by
 * focus events rather than visualViewport so it works regardless of
 * interactive-widget mode. Used to hide the bottom nav / collapse its spacer on
 * mobile when the keyboard appears.
 */
export function useKeyboardOpen(): boolean {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onFocusIn = (e: FocusEvent) => {
      if (isTextField(e.target)) setOpen(true);
    };
    const onFocusOut = () => {
      // Defer so a focus jump between two fields doesn't flicker.
      window.setTimeout(() => setOpen(isTextField(document.activeElement)), 0);
    };
    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("focusout", onFocusOut);
    return () => {
      document.removeEventListener("focusin", onFocusIn);
      document.removeEventListener("focusout", onFocusOut);
    };
  }, []);
  return open;
}
