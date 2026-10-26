import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/site-header";

export default function NotFound() {
  return <><SiteHeader /><main id="main" className="shell not-found"><p className="eyebrow">PAGE NOT FOUND</p><h1>This page isn’t<br /><em>in the collection.</em></h1><p>The publication may have moved, or the address may be incomplete.</p><Link className="read-link" href="/">Return to the collection <span aria-hidden="true">↗</span></Link></main><SiteFooter /></>;
}
