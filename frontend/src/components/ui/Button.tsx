import type { ComponentProps, ReactNode } from "react";
import { LoaderCircle } from "lucide-react";

type Variant = "primary" | "ghost";

type ButtonProps = ComponentProps<"button"> & {
  variant?: Variant;
  loading?: boolean;
  icon?: ReactNode;
};

const VARIANTS: Record<Variant, string> = {
  primary: "bg-chalk text-chalk-ink hover:bg-chalk-hover font-semibold",
  ghost: "text-fg-muted hover:text-fg hover:bg-ink-800",
};

export function Button({
  variant = "primary",
  loading = false,
  icon,
  children,
  disabled,
  className = "",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md px-3.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${VARIANTS[variant]} ${className}`}
    >
      {loading ? <LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}
