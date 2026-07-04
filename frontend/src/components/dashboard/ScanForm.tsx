"use client";

import { FormEvent, useState } from "react";

import { validateScanAddress } from "@/lib/validators";

interface ScanFormProps {
  onSubmit: (address: string) => Promise<void>;
  isSubmitting: boolean;
  disabled?: boolean;
}

export function ScanForm({ onSubmit, isSubmitting, disabled = false }: ScanFormProps) {
  const [address, setAddress] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateScanAddress(address);
    if (validationError) {
      setFieldError(validationError);
      return;
    }

    setFieldError(null);
    await onSubmit(address.trim().toLowerCase());
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="contract-address" className="mb-2 block text-sm font-medium text-foreground">
          Contract address
        </label>
        <input
          id="contract-address"
          name="contract-address"
          type="text"
          inputMode="text"
          autoComplete="off"
          spellCheck={false}
          placeholder="0x742d35cc6634c0532925a3b844bc9e7595f0beb0"
          value={address}
          disabled={disabled || isSubmitting}
          onChange={(event) => {
            setAddress(event.target.value);
            if (fieldError) {
              setFieldError(null);
            }
          }}
          className="w-full rounded-lg border border-border bg-surface-elevated px-4 py-3 font-mono text-sm text-foreground outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:opacity-60"
        />
        {fieldError ? (
          <p className="mt-2 text-sm text-risk-high" role="alert">
            {fieldError}
          </p>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground">
            Enter any EVM contract address. ChainSentinel runs governance, capability, and honeypot analysis.
          </p>
        )}
      </div>

      <button
        type="submit"
        disabled={disabled || isSubmitting}
        className="inline-flex w-full items-center justify-center rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-accent-foreground transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
      >
        {isSubmitting ? "Submitting scan…" : "Analyze contract"}
      </button>
    </form>
  );
}
