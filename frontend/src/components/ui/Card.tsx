import type { ReactNode } from "react";

interface CardProps {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

export function Card({ title, description, children, className = "" }: CardProps) {
  return (
    <section
      className={`rounded-xl border border-border bg-surface/80 p-5 shadow-sm backdrop-blur ${className}`}
    >
      <header className="mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">{title}</h2>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </header>
      {children}
    </section>
  );
}
