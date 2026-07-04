const ETH_ADDRESS_PATTERN = /^0x[a-fA-F0-9]{40}$/;

export function isValidEthAddress(value: string): boolean {
  return ETH_ADDRESS_PATTERN.test(value.trim());
}

export function normalizeEthAddress(value: string): string {
  return value.trim().toLowerCase();
}

export function validateScanAddress(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Contract address is required.";
  }
  if (!trimmed.startsWith("0x")) {
    return "Address must start with 0x.";
  }
  if (trimmed.length !== 42) {
    return "Address must be 42 characters (0x + 40 hex digits).";
  }
  if (!isValidEthAddress(trimmed)) {
    return "Address contains invalid hex characters.";
  }
  return null;
}
