import type { PublicationTab } from "../../types/study";

type Props = { tabs: PublicationTab[]; currentPublicationId: string };

// Each saved report has its own immutable route. Ordinary links preserve native
// keyboard, history and open-in-new-tab behavior without client calculations.
export function PublicationTabs({ tabs, currentPublicationId }: Props) {
  return <nav className="publication-tabs" aria-label="Study chart navigation">
    <ul>{tabs.map(tab => <li key={tab.publicationId}>
      <a href={`/reports/${tab.publicationId}/`} aria-current={tab.publicationId === currentPublicationId ? "page" : undefined}>{tab.label}</a>
    </li>)}</ul>
  </nav>;
}
