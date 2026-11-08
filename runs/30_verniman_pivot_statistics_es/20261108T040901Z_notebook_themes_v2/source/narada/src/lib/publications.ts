import { readFile } from "node:fs/promises";
import path from "node:path";
import { cache } from "react";
import type { PublicationBundle, PublicationIndex } from "../../types/report";

const publicRoot = path.join(process.cwd(), "public", "publications");
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

// These files are validated by the publication verifier before a production build.
// This module is consumed exclusively by Server Components at build time.
export const getPublicationIndex = cache(async (): Promise<PublicationIndex> => {
  const content = await readFile(path.join(publicRoot, "index.json"), "utf8");
  return JSON.parse(content) as PublicationIndex;
});

export const getPublication = cache(async (id: string): Promise<PublicationBundle | null> => {
  if (!slugPattern.test(id)) return null;
  const index = await getPublicationIndex();
  if (!index.reports.some((report) => report.id === id)) return null;
  const content = await readFile(path.join(publicRoot, id, "report.json"), "utf8");
  return JSON.parse(content) as PublicationBundle;
});
