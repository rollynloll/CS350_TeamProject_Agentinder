import { useEffect, useState } from "react";

/**
 * The visual viewport's bottom edge in layout coordinates (offsetTop + height),
 * but only while the on-screen keyboard is up — otherwise null.
 *
 * iOS mis-handles `position: fixed; bottom: 0` when the keyboard opens (the bar
 * floats or hides). The fix (per the WebKit/PWA community) is to position with
 * `top: <this value>` + `transform: translateY(-100%)` so the element's bottom
 * sits exactly on the visual viewport's bottom — i.e. flush above the keyboard.
 */
export function useVisualViewportBottom(): number | null {
  const [bottom, setBottom] = useState<number | null>(null);
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const onChange = () => {
      const keyboardUp = window.innerHeight - vv.height > 80;
      setBottom(keyboardUp ? vv.offsetTop + vv.height : null);
    };
    onChange();
    vv.addEventListener("resize", onChange);
    vv.addEventListener("scroll", onChange);
    return () => {
      vv.removeEventListener("resize", onChange);
      vv.removeEventListener("scroll", onChange);
    };
  }, []);
  return bottom;
}
