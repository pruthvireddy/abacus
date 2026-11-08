"use client";

import Link from "next/link";

type TabLink = { href: string; label: string; current?: boolean };

// Serialize only navigation identities, not a separate client boundary for each
// server-authored link. The rendered anchors also work without JavaScript.
export function StudyTabList({ links, preserveScroll = false }: { links: TabLink[]; preserveScroll?: boolean }) {
  return <ul>{links.map(link => <li key={link.href}><Link href={link.href} prefetch={false} scroll={!preserveScroll} aria-current={link.current ? "page" : undefined}>{link.label}</Link></li>)}</ul>;
}
