import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { StudyDestination } from "../../../../../types/study";
import { getStudy, getStudyCatalog } from "@/lib/studies";
import { StudyExperiencePage } from "@/components/study-experience";
import { STUDY_DESTINATIONS } from "../../../../../scripts/lib/study-routes.mjs";

export const dynamicParams = false;
export async function generateStaticParams() {
  const { studies } = await getStudyCatalog();
  return studies.length ? studies.flatMap(({ slug }) => STUDY_DESTINATIONS.filter(destination => destination.path).map(destination => ({ slug, destination: destination.path }))) : [{ slug: "__narada_empty__", destination: "findings" }];
}
type Props = { params: Promise<{ slug: string; destination: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug, destination } = await params;
  const study = await getStudy(slug);
  const section = STUDY_DESTINATIONS.find(candidate => candidate.path === destination && candidate.path);
  return study && section ? { title: `${section.label} · ${study.title}`, description: study.summary } : { title: "Study destination not found", robots: { index: false, follow: false } };
}
export default async function StudyDestinationPage({ params }: Props) {
  const { slug, destination } = await params;
  const study = await getStudy(slug);
  const section = STUDY_DESTINATIONS.find(candidate => candidate.path === destination && candidate.path);
  if (!study || !section) notFound();
  return <StudyExperiencePage study={study} destination={section.key as StudyDestination} />;
}
