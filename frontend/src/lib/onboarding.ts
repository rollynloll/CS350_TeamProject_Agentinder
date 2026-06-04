// Client-only onboarding completion flag. Kept separate from the auth store so
// logging out does not re-trigger the tutorial. Local-only by design: a new
// device/browser re-shows onboarding (accepted tradeoff).
const KEY = "agentinder.onboarded";

export function isOnboarded(): boolean {
  try {
    return localStorage.getItem(KEY) === "true";
  } catch {
    return false;
  }
}

export function markOnboarded(): void {
  try {
    localStorage.setItem(KEY, "true");
  } catch {
    /* storage unavailable — gate will simply re-show onboarding */
  }
}
