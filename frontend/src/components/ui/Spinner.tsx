interface SpinnerProps {
  label?: string;
  size?: "sm" | "md";
}

export function Spinner({ label, size = "md" }: SpinnerProps) {
  const dimension = size === "sm" ? "h-4 w-4" : "h-6 w-6";

  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground" role="status">
      <span
        className={`inline-block animate-spin rounded-full border-2 border-accent/30 border-t-accent ${dimension}`}
        aria-hidden
      />
      {label ? <span>{label}</span> : <span className="sr-only">Loading</span>}
    </div>
  );
}
