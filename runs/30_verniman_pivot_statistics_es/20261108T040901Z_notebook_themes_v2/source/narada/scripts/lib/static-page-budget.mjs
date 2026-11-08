import assert from 'node:assert/strict';
import { extname } from 'node:path';

export const HTML_PAGE_MAX_BYTES = 768 * 1024;
export const RSC_PAGE_MAX_BYTES = 512 * 1024;

// Rendering adds table markup and serialized React payloads to the separately
// bounded source content. Publication/asset budgets remain with their validator.
export function assertPagePayloadSize(file, bytes) {
  const extension = extname(file);
  const budget = extension === '.html' ? HTML_PAGE_MAX_BYTES
    : ['.txt', '.rsc'].includes(extension) ? RSC_PAGE_MAX_BYTES : null;
  if (budget === null) return false;
  assert(Number.isSafeInteger(bytes) && bytes >= 0, 'Static page byte count must be a nonnegative integer.');
  assert(bytes <= budget, `${file} exceeds its static page budget.`);
  return true;
}
