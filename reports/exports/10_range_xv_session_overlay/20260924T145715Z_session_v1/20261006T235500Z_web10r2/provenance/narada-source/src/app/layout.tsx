import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Narada — Abacus publications", template: "%s — Narada" },
  description: "A considered collection of Abacus research, findings, and evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><a href="#main" className="skip-link">Skip to content</a>{children}</body>
    </html>
  );
}
