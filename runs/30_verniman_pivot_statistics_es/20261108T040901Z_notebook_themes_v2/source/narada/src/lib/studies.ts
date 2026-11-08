import { cache } from "react";
import { readStudyCatalog, findStudy, findPublicationStudy } from "../../scripts/lib/studies.mjs";
import { getPublicationIndex } from "./publications";
import type { Study, StudyCatalog } from "../../types/study";

export const getStudyCatalog = cache(async (): Promise<StudyCatalog> => {
  const { reports } = await getPublicationIndex();
  return readStudyCatalog(reports);
});
export const getPublicationStudy = cache(async (id: string) => findPublicationStudy(await getStudyCatalog(), id));
export const getStudy = cache(async (slug: string): Promise<Study | null> => {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) return null;
  return findStudy(await getStudyCatalog(), slug);
});
