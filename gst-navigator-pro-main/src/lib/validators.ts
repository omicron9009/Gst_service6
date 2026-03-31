export const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

export function validateGSTIN(gstin: string): boolean {
  return GSTIN_REGEX.test(gstin);
}

export function maskGSTIN(gstin: string): string {
  if (gstin.length < 4) return gstin;
  return gstin.slice(0, 2) + '*'.repeat(gstin.length - 4) + gstin.slice(-2);
}
