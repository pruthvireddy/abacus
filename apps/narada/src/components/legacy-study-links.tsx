import type { PublicationBundle } from "../../types/report";
import { legacyStudyAnchors } from "../../scripts/lib/study-routes.mjs";

// Fragments are never sent to a server. CSS :target reveals an explicit link to
// the saved destination without redirect scripts or hidden full report bodies.
export function LegacyStudyLinks({ featured }: { featured: PublicationBundle }) {
  const anchors = legacyStudyAnchors(featured);
  return <aside className="legacy-study-links" aria-label="Saved section link compatibility">
    <div className="legacy-link-targets">{anchors.map(anchor => <p className="legacy-study-target" id={anchor.id} key={anchor.id}>This saved section is available in the detailed report. <a href={anchor.href}>Continue to {anchor.label} <span aria-hidden="true">↗</span></a></p>)}</div>
    <details><summary>Following an older study-section link?</summary><p>Saved report sections now have their own detailed destination. Earlier study links retain a route to the same saved content.</p><ul>{anchors.map(anchor => <li key={anchor.id}><a href={anchor.href}>{anchor.label}</a></li>)}</ul></details>
  </aside>;
}
