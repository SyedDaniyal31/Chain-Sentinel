"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorAlert } from "@/components/dashboard/ErrorAlert";
import { PaginationControls } from "@/components/history/PaginationControls";
import { ScanHistoryTable } from "@/components/history/ScanHistoryTable";
import { SummaryCards } from "@/components/history/SummaryCards";
import { AppHeader } from "@/components/layout/AppHeader";
import { Spinner } from "@/components/ui/Spinner";
import { getScanSummary, getScans } from "@/lib/api";
import type { PaginatedScanResponse, ScanSummaryResponse } from "@/types/scan";
import { ApiError } from "@/types/scan";

const PAGE_SIZE = 20;

export function ScanHistoryPage() {
  const [page, setPage] = useState(1);
  const [scans, setScans] = useState<PaginatedScanResponse | null>(null);
  const [summary, setSummary] = useState<ScanSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async (targetPage: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const [scanPage, scanSummary] = await Promise.all([
        getScans({ page: targetPage, page_size: PAGE_SIZE }),
        getScanSummary(),
      ]);
      setScans(scanPage);
      setSummary(scanSummary);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to load scan history. Ensure the backend is running.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHistory(page);
  }, [loadHistory, page]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <AppHeader active="history" />

      <div className="mb-6">
        <h2 className="text-xl font-semibold text-foreground">Scan History</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse historical scans, risk trends, and drill into individual intelligence reports.
        </p>
      </div>

      {error ? <ErrorAlert message={error} onDismiss={() => setError(null)} /> : null}

      {isLoading ? (
        <div className="flex min-h-[240px] items-center justify-center rounded-xl border border-border bg-surface/50">
          <Spinner label="Loading scan history…" />
        </div>
      ) : (
        <div className="space-y-6">
          {summary ? <SummaryCards summary={summary} /> : null}
          {scans ? (
            <>
              <ScanHistoryTable items={scans.items} />
              <PaginationControls
                page={scans.page}
                totalPages={scans.total_pages}
                total={scans.total}
                pageSize={scans.page_size}
                onPageChange={setPage}
              />
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
