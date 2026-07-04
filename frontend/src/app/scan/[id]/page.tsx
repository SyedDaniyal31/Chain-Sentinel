import { ScanDetailView } from "@/components/scan/ScanDetailView";

interface ScanDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function ScanDetailPage({ params }: ScanDetailPageProps) {
  const { id } = await params;
  const scanId = Number.parseInt(id, 10);

  if (!Number.isFinite(scanId) || scanId < 1) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 text-center">
        <h1 className="text-xl font-semibold text-foreground">Invalid scan ID</h1>
      </div>
    );
  }

  return <ScanDetailView scanId={scanId} />;
}
