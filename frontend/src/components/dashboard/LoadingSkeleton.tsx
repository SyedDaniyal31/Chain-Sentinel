import { Card } from "@/components/ui/Card";

function Block({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-surface-elevated ${className}`} />;
}

export function LoadingSkeleton() {
  return (
    <div className="space-y-6" aria-busy aria-label="Loading scan results">
      <Card title="Risk score" description="Loading intelligence…">
        <Block className="h-24 w-full" />
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Governance">
          <Block className="mb-3 h-10 w-full" />
          <Block className="mb-3 h-10 w-full" />
          <Block className="h-10 w-full" />
        </Card>
        <Card title="Capabilities">
          <div className="grid gap-3 sm:grid-cols-2">
            <Block className="h-24 w-full" />
            <Block className="h-24 w-full" />
            <Block className="h-24 w-full" />
            <Block className="h-24 w-full" />
          </div>
        </Card>
      </div>
      <Card title="Honeypot & trading">
        <Block className="h-32 w-full" />
      </Card>
      <Card title="Risk findings">
        <Block className="mb-2 h-10 w-full" />
        <Block className="mb-2 h-10 w-full" />
        <Block className="h-10 w-full" />
      </Card>
    </div>
  );
}
