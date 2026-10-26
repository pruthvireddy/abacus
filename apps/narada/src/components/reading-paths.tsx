import type { ReadingPath, Study } from "../../types/study";
import { studyDestinationHref } from "../../scripts/lib/study-routes.mjs";

export function ReadingPaths({ paths, studies }: { paths: ReadingPath[]; studies: Study[] }) {
  const byId = new Map(studies.map(study => [study.studyId, study]));
  return paths.length ? <section className="reading-paths" id="reading-paths" aria-labelledby="reading-paths-title"><div className="collection-heading"><div><p className="eyebrow">CURATED READING</p><h2 id="reading-paths-title">Follow a research question</h2></div><span>{paths.length} reading paths</span></div><p className="section-intro">An authored reading order connects related questions. Each study retains its own populations, findings, and evidence limits.</p><div className="reading-path-grid">{paths.map(path => <article className="reading-path" id={`reading-path-${path.id}`} key={path.id}>
    <h3>{path.title}</h3><p className="reading-path-description">{path.description}</p><p className="reading-path-qualification">{path.qualification}</p>
    <ol>{path.steps.map(step => {
      const study = byId.get(step.studyId)!;
      return <li key={step.studyId}><a href={studyDestinationHref(study.slug, step.destination)}>{study.title}<span aria-hidden="true"> ↗</span></a><p>{step.reason}</p><p className="path-step-evidence">{study.resolvedOverview?.qualification ?? study.evidenceStatus}</p></li>;
    })}</ol>
    <a className="reading-path-anchor" href={`#reading-path-${path.id}`}>Link to this path <span aria-hidden="true">#</span></a>
  </article>)}</div></section> : null;
}

export function StudyReadingPaths({ study, paths, studies }: { study: Study; paths: ReadingPath[]; studies: Study[] }) {
  const memberships = paths.filter(path => path.steps.some(step => step.studyId === study.studyId));
  const byId = new Map(studies.map(item => [item.studyId, item]));
  return memberships.length ? <aside className="study-reading-paths" aria-labelledby="study-reading-paths-title"><p className="eyebrow">CONTINUE READING</p><h2 id="study-reading-paths-title">This study in context</h2>{memberships.map(path => {
    const position = path.steps.findIndex(step => step.studyId === study.studyId);
    const next = path.steps[position + 1];
    const nextStudy = next ? byId.get(next.studyId) : null;
    return <div key={path.id}><h3><a href={`/#reading-path-${path.id}`}>{path.title}</a></h3><p>{path.qualification}</p>{next && nextStudy ? <a className="read-link" href={studyDestinationHref(nextStudy.slug, next.destination)}>Next in this path: {nextStudy.title} <span aria-hidden="true">→</span></a> : <a className="read-link" href={`/#reading-path-${path.id}`}>Revisit the reading path <span aria-hidden="true">→</span></a>}</div>;
  })}</aside> : null;
}
