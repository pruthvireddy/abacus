import type { PublicationBundle, TableSection } from "../../types/report";

const requests = new Map<string, Promise<TableSection[]>>();
const MAX_SAVED_BUNDLE_BYTES = 4 * 1024 * 1024;

// Multiple table controls share one fetch of the already-published static JSON.
// This contains saved rows only; no endpoint or calculation is introduced.
export function loadSavedTables(reportId: string): Promise<TableSection[]> {
  const existing = requests.get(reportId);
  if (existing) return existing;
  const request = (async () => {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(reportId)) throw new Error("Invalid saved publication identity.");
    const response = await fetch(`/publications/${reportId}/report.json`);
    if (!response.ok) throw new Error("Saved publication unavailable.");
    const declaredSize = Number(response.headers.get("content-length"));
    if (Number.isFinite(declaredSize) && declaredSize > MAX_SAVED_BUNDLE_BYTES) throw new Error("Saved publication exceeds its byte bound.");
    const text = await response.text();
    if (new TextEncoder().encode(text).length > MAX_SAVED_BUNDLE_BYTES) throw new Error("Saved publication exceeds its byte bound.");
    const publication = JSON.parse(text) as PublicationBundle;
    if (publication.report.id !== reportId) throw new Error("Saved publication identity changed.");
    return publication.report.sections.filter((section): section is TableSection => section.kind === "table");
  })();
  requests.set(reportId, request);
  request.catch(() => requests.delete(reportId));
  return request;
}
