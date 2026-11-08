import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getStudy, getStudyCatalog } from "@/lib/studies";
import { StudyExperiencePage } from "@/components/study-experience";

export const dynamicParams = false;
export async function generateStaticParams() {
  const { studies } = await getStudyCatalog();
  return studies.length ? studies.map(({ slug }) => ({ slug })) : [{ slug: "__narada_empty__" }];
}
type Props = { params: Promise<{ slug: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const study = await getStudy((await params).slug);
  return study ? { title: study.title, description: study.summary } : { title: "Study not found", robots: { index: false, follow: false } };
}
export default async function StudyPage({ params }: Props) {
  const study = await getStudy((await params).slug);
  if (!study) notFound();
  return <StudyExperiencePage study={study} destination="overview" />;
}
