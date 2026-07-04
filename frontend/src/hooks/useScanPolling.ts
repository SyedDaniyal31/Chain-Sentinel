"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getScan } from "@/lib/api";
import type { ScanJob } from "@/types/scan";
import { ApiError, TERMINAL_STATUSES } from "@/types/scan";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 90;

interface UseScanPollingResult {
  scan: ScanJob | null;
  isPolling: boolean;
  error: string | null;
  pollCount: number;
  startPolling: (scanId: number) => void;
  reset: () => void;
}

export function useScanPolling(): UseScanPollingResult {
  const [scan, setScan] = useState<ScanJob | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const scanIdRef = useRef<number | null>(null);
  const attemptsRef = useRef(0);

  const reset = useCallback(() => {
    scanIdRef.current = null;
    attemptsRef.current = 0;
    setScan(null);
    setIsPolling(false);
    setError(null);
    setPollCount(0);
  }, []);

  const fetchOnce = useCallback(async (scanId: number) => {
    try {
      const job = await getScan(scanId);
      setScan(job);
      setPollCount((count) => count + 1);
      setError(null);

      if (TERMINAL_STATUSES.includes(job.status)) {
        setIsPolling(false);
        scanIdRef.current = null;
        if (job.status === "failed") {
          setError("Scan job failed on the server. Check backend logs and RPC connectivity.");
        }
        return true;
      }

      attemptsRef.current += 1;
      if (attemptsRef.current >= MAX_POLL_ATTEMPTS) {
        setIsPolling(false);
        scanIdRef.current = null;
        setError("Scan timed out while waiting for completion. Try again later.");
        return true;
      }

      return false;
    } catch (err) {
      setIsPolling(false);
      scanIdRef.current = null;
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to reach ChainSentinel API. Is the backend running?");
      }
      return true;
    }
  }, []);

  const startPolling = useCallback(
    (scanId: number) => {
      reset();
      scanIdRef.current = scanId;
      attemptsRef.current = 0;
      setIsPolling(true);
      void fetchOnce(scanId);
    },
    [fetchOnce, reset],
  );

  useEffect(() => {
    if (!isPolling || scanIdRef.current === null) {
      return;
    }

    const intervalId = window.setInterval(() => {
      const scanId = scanIdRef.current;
      if (scanId === null) {
        return;
      }
      void fetchOnce(scanId).then((done) => {
        if (done) {
          window.clearInterval(intervalId);
        }
      });
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [fetchOnce, isPolling]);

  return {
    scan,
    isPolling,
    error,
    pollCount,
    startPolling,
    reset,
  };
}
