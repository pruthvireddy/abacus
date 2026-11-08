import type { PublicationTab } from "../../types/study";
import { StudyTabList } from "./study-tab-list";

type Props = { tabs: PublicationTab[]; currentPublicationId: string; variant?: "views" | "themes" };

// Each saved report has its own immutable route. Ordinary links preserve native
// keyboard, history and open-in-new-tab behavior without client calculations.
export function PublicationTabs({ tabs, currentPublicationId, variant = "views" }: Props) {
  const themes = variant === "themes";
  return <nav className={`publication-tabs${themes ? " publication-theme-tabs" : ""}`} aria-label={themes ? "Study question themes" : "Study chart navigation"}>
    <p className="eyebrow">{themes ? "QUESTION THEMES" : "SAVED VIEW"}</p>
    <StudyTabList preserveScroll links={tabs.map(tab => ({ href: `/reports/${tab.publicationId}/`, label: tab.label, current: tab.publicationId === currentPublicationId }))} />
  </nav>;
}
