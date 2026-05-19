import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  asChild?: boolean;
};

const variantClass: Record<Variant, string> = {
  primary: "bg-primary text-primary-fg hover:opacity-90",
  secondary: "bg-surface-2 text-text hover:bg-border",
  ghost: "bg-transparent text-text hover:bg-surface-2",
  danger: "bg-danger text-white hover:opacity-90",
};

const sizeClass: Record<Size, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { className, variant = "primary", size = "md", asChild = false, ...rest },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition disabled:opacity-50 disabled:cursor-not-allowed",
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      {...rest}
    />
  );
});
