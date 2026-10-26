import Link from "next/link";

export function SiteHeader({ title }: { title?: string }) {
  return (
    <header className="site-header shell">
      <Link href="/" className="brand" aria-label="Abacus Narada, study library">
        <span className="brand-symbol" aria-hidden="true">a.</span>
        <span>ABACUS <span className="brand-divider">/</span> NARADA</span>
      </Link>
      {title ? <span className="nav-title">{title}</span> : <span className="nav-caption">Research, considered.</span>}
      {title ? <Link href="/" className="back-link">Study library <span aria-hidden="true">↗</span></Link> : null}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer shell">
      <Link href="/" className="footer-brand">Abacus / Narada</Link>
      <p>A place for research and its evidence.</p>
    </footer>
  );
}
