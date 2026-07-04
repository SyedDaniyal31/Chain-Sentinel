import type { ReactNode } from "react";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "neutral";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  default: "border-accent/30 bg-accent/10 text-accent",
  success: "border-risk-low/30 bg-risk-low/10 text-risk-low",
  warning: "border-risk-medium/30 bg-risk-medium/10 text-risk-medium",
  danger: "border-risk-high/30 bg-risk-high/10 text-risk-high",
  neutral: "border-border bg-surface-elevated text-muted-foreground",
};

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${VARIANT_CLASSES[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
