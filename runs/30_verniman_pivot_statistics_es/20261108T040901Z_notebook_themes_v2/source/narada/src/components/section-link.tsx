// Every heading has a native permalink; clipboard enhancement is shared by the
// contents rail instead of mounting a separate client component per section.
export function SectionLink({ sectionId }: { sectionId: string }) {
  return <a className="section-permalink" href={`#section-${sectionId}`} aria-label="Direct section link">#</a>;
}
