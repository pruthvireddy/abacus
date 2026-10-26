import type { StudyAnalysis, StudyPhaseFamily } from "../../types/study";
import { familyPublicationSelection } from "../../scripts/lib/study-selections.mjs";

type Props = { analyses: StudyAnalysis[]; currentAnalysisId?: string; currentChartLabel?: string; asConditions?: boolean };

// Analysis switches preserve an explicitly authored chart label where possible.
// Every destination remains an immutable saved publication, with no merging.
export function StudyAnalysisNavigation({ analyses, currentAnalysisId, currentChartLabel, asConditions = false }: Props) {
  return <nav className="study-analyses" aria-label="Study analysis navigation">
    <p className="eyebrow">{asConditions ? "CHOOSE A CONDITION" : "CHOOSE AN ANALYSIS"}</p>
    <ul>{analyses.map(analysis => {
      const selected = analysis.publicationTabs.find(tab => tab.label === currentChartLabel) ?? analysis.publicationTabs[0];
      return <li key={analysis.id}><a href={`/reports/${selected.publicationId}/`} aria-current={analysis.id === currentAnalysisId ? "page" : undefined}>{analysis.label}</a></li>;
    })}</ul>
  </nav>;
}

export function StudyPhaseNavigation({ families, currentFamilyId, currentAnalysisId, currentChartLabel }: {
  families: StudyPhaseFamily[]; currentFamilyId?: string; currentAnalysisId?: string; currentChartLabel?: string;
}) {
  return <nav className="study-phases" aria-label="Study phase navigation">
    <p className="eyebrow">CHOOSE A PHASE</p>
    <ul>{families.map(family => {
      const { tab } = familyPublicationSelection(family, currentAnalysisId, currentChartLabel);
      return <li key={family.id}><a href={`/reports/${tab.publicationId}/`} aria-current={family.id === currentFamilyId ? "page" : undefined}>{family.label}</a></li>;
    })}</ul>
  </nav>;
}

function AnalysisLinks({ analyses }: { analyses: StudyAnalysis[] }) {
  return <ul>{analyses.map(analysis => <li key={analysis.id}><span>{analysis.label}</span><ul>{analysis.publicationTabs.map(tab => <li key={tab.publicationId}><a href={`/reports/${tab.publicationId}/`}>{tab.label}</a></li>)}</ul></li>)}</ul>;
}

export function StudyAnalysisDirectory({ analyses }: { analyses: StudyAnalysis[] }) {
  return <details className="analysis-directory">
    <summary>Browse every analysis and chart</summary>
    <AnalysisLinks analyses={analyses} />
  </details>;
}

export function StudyPhaseDirectory({ families }: { families: StudyPhaseFamily[] }) {
  return <details className="analysis-directory phase-directory">
    <summary>Browse every phase, condition and chart</summary>
    <ul>{families.map(family => <li key={family.id}><span>{family.label}</span><AnalysisLinks analyses={family.analyses} /></li>)}</ul>
  </details>;
}
