export const PRIORITY_BAND_LABELS = {
  1: "Pause",
  2: "Define and test",
  3: "Targeted follow-up",
  4: "Strong candidate",
  5: "Highest priority",
};
export const PRIORITY_STATE_LABELS = {
  not_assessed: "Not assessed",
  needs_review: "Needs review",
  not_applicable: "Not applicable",
};
export const PRIORITY_FILTER_OPTIONS = [
  ...[1, 2, 3, 4, 5].map(score => ({ value: String(score), label: String(score) + "/5 — " + PRIORITY_BAND_LABELS[score] })),
  { value: "not_assessed", label: PRIORITY_STATE_LABELS.not_assessed },
  { value: "needs_review", label: PRIORITY_STATE_LABELS.needs_review },
  { value: "not_applicable", label: PRIORITY_STATE_LABELS.not_applicable },
];

// Only current numeric assessments participate in discovery ranking. A retained
// previous score is context, even though the full assessment stays on the server.
/** @param {import("../../types/study").Study} study */
export function priorityPresentation(study) {
  const assessment = study.resolvedResearchPriority ?? study.researchPriority;
  const state = study.resolvedResearchPriority?.effectiveState
    ?? (assessment?.reassessment?.required ? "needs_review" : assessment?.state ?? "not_assessed");
  if (!["assessed", "not_assessed", "needs_review", "not_applicable"].includes(state)) {
    throw new Error("Unknown research-priority state.");
  }
  const score = state === "assessed" ? assessment?.score : undefined;
  if (state === "assessed" && (!Number.isInteger(score) || score === undefined || score < 1 || score > 5)) {
    throw new Error("A current research-priority assessment requires an integer score from 1 to 5.");
  }
  const label = score !== undefined ? PRIORITY_BAND_LABELS[score] : PRIORITY_STATE_LABELS[state];
  return { state, score: score ?? null, label, assessment };
}

/** @param {import("../../types/study").Study} study */
export function priorityAccessibleLabel(study) {
  const { score, label } = priorityPresentation(study);
  return "Research priority: " + (score === null ? label : String(score) + " out of 5 — " + label) + ".";
}
