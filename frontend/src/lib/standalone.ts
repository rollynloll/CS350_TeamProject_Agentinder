/**
 * True when the app runs as an installed PWA ("Add to Home Screen"), where the
 * real OS status bar overlays the top and there is no browser chrome. Used to
 * drop the mock StatusBar and lean on the device safe-area insets instead.
 */
export function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  const displayMode = window.matchMedia?.("(display-mode: standalone)").matches ?? false;
  // iOS Safari exposes a non-standard navigator.standalone for home-screen apps.
  const iosStandalone =
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true;
  return displayMode || iosStandalone;
}
