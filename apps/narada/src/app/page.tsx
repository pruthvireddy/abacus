import { SiteFooter, SiteHeader } from "@/components/site-header";
import { StudyCard } from "@/components/study-card";
import { getStudyCatalog } from "@/lib/studies";
import { buildDiscoveryIndex } from "@/lib/discovery";
import { LibraryDiscovery } from "@/components/library-discovery";
import { ReadingPaths } from "@/components/reading-paths";
import { ResearchPriorityRubric } from "@/components/research-priority";

// This is an editorial starting set, never a ranking by result or date.
const startingSlugs = ["session-vwap", "gc-overnight-breakout-15m", "forex-news-ema", "nq-advanced-amd-video"];

export default async function LibraryPage() {
  const { studies, readingPaths = [], researchPriorityRubric } = await getStudyCatalog();
  const startingStudies = startingSlugs.flatMap(slug => studies.find(study => study.slug === slug) ?? []);
  return <>
    <SiteHeader />
    <main id="main" className="shell library-main">
      <section className="library-intro library-intro-brief" aria-labelledby="library-title">
        <div><p className="eyebrow"><span /> THE RESEARCH LIBRARY</p><h1 id="library-title">Ideas, examined.<br /><em>Evidence, shared.</em></h1></div>
        <div><p className="intro-copy">Market questions, saved findings, and the limits of what they tell us. Start with a study, then follow the evidence.</p><nav className="library-quick-links" aria-label="Library browsing"><a href="#publications-title">Browse the collection ↓</a>{readingPaths.length ? <a href="#reading-paths">Curated reading paths ↓</a> : null}{researchPriorityRubric ? <a href="#research-priority-rubric">Research priority rubric ↓</a> : null}</nav></div>
      </section>
      {startingStudies.length ? <details className="library-starting-points"><summary>Four starting points across the research</summary><section className="curated-starts" aria-labelledby="starting-title">
        <div className="curated-intro"><p className="eyebrow">SELECTED STARTING POINTS</p><h2 id="starting-title">Four ways into the research</h2><p>A curated introduction to numerical studies, frozen decisions, and source reviews.</p></div>
        <ol>{startingStudies.map((study, index) => <li key={study.slug}><a href={`/studies/${study.slug}/`}><span className="curated-number">0{index + 1}</span><span><strong>{study.title}</strong><small>{study.resolvedOverview?.evidenceType ?? study.topic}</small></span><span aria-hidden="true">↗</span></a></li>)}</ol>
      </section></details> : null}
      <section className="publications" aria-labelledby="publications-title">
        <div className="collection-heading"><div><p className="eyebrow">BROWSE THE LIBRARY</p><h2 id="publications-title">The collection</h2></div><span>{studies.length} {studies.length === 1 ? "study" : "studies"}</span></div>
        {studies.length ? <LibraryDiscovery entries={buildDiscoveryIndex(studies)}>{studies.map((study, index) => <StudyCard study={study} number={index + 1} key={study.studyId} />)}</LibraryDiscovery> : <div className="empty-collection"><h3>The first pages are still to come.</h3><p>New studies will appear here when selected research is ready to share.</p></div>}
      </section>
      <ReadingPaths paths={readingPaths} studies={studies} />
      <ResearchPriorityRubric rubric={researchPriorityRubric} />
    </main><SiteFooter />
  </>;
}
