import * as RadixAvatar from "@radix-ui/react-avatar";
import { cn } from "@/lib/cn";

type Size = "sm" | "md" | "lg" | "xl";

const sizeClass: Record<Size, string> = {
  sm: "w-8 h-8 text-xs",
  md: "w-10 h-10 text-sm",
  lg: "w-14 h-14 text-base",
  xl: "w-24 h-24 text-2xl",
};

export function Avatar({
  src,
  name,
  size = "md",
  className,
}: {
  src?: string | null;
  name: string;
  size?: Size;
  className?: string;
}) {
  const initials = name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <RadixAvatar.Root
      className={cn(
        "inline-flex items-center justify-center overflow-hidden rounded-full bg-surface-2",
        sizeClass[size],
        className,
      )}
    >
      {src ? (
        <RadixAvatar.Image src={src} alt={name} className="h-full w-full object-cover" />
      ) : null}
      <RadixAvatar.Fallback className="text-text-muted font-medium">
        {initials}
      </RadixAvatar.Fallback>
    </RadixAvatar.Root>
  );
}
