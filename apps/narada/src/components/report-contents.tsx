"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

type Entry = { id: string; title: string };
type Props = { sections: Entry[]; downloads?: boolean; references?: boolean; notes?: boolean };
const subscribeCopy = () => () => {};
const browserCopy = () => typeof navigator !== "undefined" && typeof navigator.clipboard?.writeText === "function";
const serverCopy = () => false;

// Only section identities and titles cross this client boundary, never bodies or
// table rows. Native anchors and the mobile disclosure remain useful without JS.
export function ReportContents({ sections, downloads, references, notes }: Props) {
  const [current, setCurrent] = useState<string | null>(null);
  const [copied, setCopied] = useState<{ id: string; message: string } | null>(null);
  const canCopy = useSyncExternalStore(subscribeCopy, browserCopy, serverCopy);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const ids = [...sections.map(section => `section-${section.id}`), ...(downloads ? ["publication-downloads"] : []), ...(references ? ["publication-references"] : []), ...(notes ? ["publication-notes"] : []), "publication-record"];
    const elements = ids.map(id => document.getElementById(id)).filter((element): element is HTMLElement => element !== null);
    const visible = new Set<string>();
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) visible.add(entry.target.id);
        else visible.delete(entry.target.id);
      }
      const nearest = elements.filter(element => visible.has(element.id)).sort((a, b) => Math.abs(a.getBoundingClientRect().top - 80) - Math.abs(b.getBoundingClientRect().top - 80))[0];
      if (nearest) setCurrent(nearest.id);
    }, { rootMargin: "-5% 0px -60% 0px", threshold: 0 });
    elements.forEach(element => observer.observe(element));
    return () => observer.disconnect();
  }, [sections, downloads, references, notes]);
  const target = current ?? (sections[0] ? `section-${sections[0].id}` : "publication-record");
  const targetTitle = sections.find(section => `section-${section.id}` === target)?.title ?? ({ "publication-downloads": "Evidence downloads", "publication-references": "Source references", "publication-notes": "Notes", "publication-record": "Publication record" }[target] ?? "Current section");
  async function copySection() {
    try {
      await navigator.clipboard.writeText(new URL(`${window.location.pathname}#${target}`, window.location.origin).href);
      setCopied({ id: target, message: "Section link copied." });
    } catch {
      setCopied({ id: target, message: "Use the heading’s # link." });
    }
  }
  const links = <><div className="contents-copy-controls"><button type="button" onClick={copySection} disabled={!canCopy}>Copy section link</button><small>{targetTitle}</small><span role="status" aria-live="polite">{copied?.id === target ? copied.message : ""}</span></div><ol>{sections.map(section => <li key={section.id}><a href={`#section-${section.id}`} aria-current={current === `section-${section.id}` ? "location" : undefined}>{section.title}</a></li>)}</ol>
    {downloads ? <a href="#publication-downloads" className="contents-note" aria-current={current === "publication-downloads" ? "location" : undefined}>Evidence downloads</a> : null}
    {references ? <a href="#publication-references" className="contents-note" aria-current={current === "publication-references" ? "location" : undefined}>Source references</a> : null}
    {notes ? <a href="#publication-notes" className="contents-note" aria-current={current === "publication-notes" ? "location" : undefined}>Notes</a> : null}
    <a href="#publication-record" className="contents-note" aria-current={current === "publication-record" ? "location" : undefined}>Publication record</a>
  </>;
  return <aside className="reader-contents">
    <nav className="contents contents-desktop" aria-label="Publication contents"><span className="eyebrow">IN THIS PUBLICATION</span>{links}</nav>
    <details className="contents-mobile"><summary>Contents <span>{sections.length} sections</span></summary><nav className="contents" aria-label="Mobile publication contents">{links}</nav></details>
  </aside>;
}
