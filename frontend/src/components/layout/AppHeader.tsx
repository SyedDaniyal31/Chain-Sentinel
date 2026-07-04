import Image from "next/image";
import Link from "next/link";

interface AppHeaderProps {
  active?: "dashboard" | "history";
}

export function AppHeader({ active = "dashboard" }: AppHeaderProps) {
  return (
    <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
      <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-90">
        <Image
          src="/chainsentinel-logo.png"
          alt="ChainSentinel"
          width={48}
          height={48}
          className="h-12 w-12 shrink-0 rounded-full object-cover"
          priority
        />
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">ChainSentinel</h1>
          <p className="text-sm text-muted-foreground">Blockchain security intelligence platform</p>
        </div>
      </Link>

      <nav className="flex items-center gap-2">
        <Link
          href="/"
          className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
            active === "dashboard"
              ? "bg-accent/15 text-accent"
              : "text-muted-foreground hover:bg-surface-elevated hover:text-foreground"
          }`}
        >
          Dashboard
        </Link>
        <Link
          href="/history"
          className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
            active === "history"
              ? "bg-accent/15 text-accent"
              : "text-muted-foreground hover:bg-surface-elevated hover:text-foreground"
          }`}
        >
          History
        </Link>
      </nav>
    </header>
  );
}
