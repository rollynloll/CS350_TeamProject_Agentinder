import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// Register the project's custom font-size tokens so tailwind-merge treats e.g.
// `text-caption` as a font-size (not a colour). Without this it sees both
// `text-caption` and `text-tier-trusted-text` as `text-*` and drops one.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["caption", "body2", "body1", "h3", "h2", "display"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
