import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cartridge Club — Compatibility Finder",
  description:
    "Find accessories that actually work with your retro console.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="cc-header">
          <Link href="/" className="cc-header__brand">
            Cartridge Club <span aria-hidden>·</span> Compatibility Finder
          </Link>
          <nav className="cc-header__nav">
            <Link href="/search">Search</Link>
            <Link href="/cart">Cart</Link>
          </nav>
        </header>
        <main className="cc-main">{children}</main>
        <footer className="cc-footer">
          <p>
            Sandbox project. Built against the Shopify Storefront API. See the
            repo README for setup.
          </p>
        </footer>
      </body>
    </html>
  );
}
