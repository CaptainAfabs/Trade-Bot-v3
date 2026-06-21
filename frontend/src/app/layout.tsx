import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Stock Advisor",
  description: "Personalized AI stock recommendations.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-cream text-ink">
        <header className="border-b border-cream-300 bg-cream-50">
          <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
            <Link
              href="/"
              className="flex items-center gap-2 text-brg font-semibold tracking-tight"
            >
              <span
                aria-hidden
                className="inline-block h-3 w-3 rounded-full bg-brg"
              />
              <span className="text-lg">Stock Advisor</span>
            </Link>
            <nav className="flex items-center gap-5 text-sm text-ink-muted">
              <Link href="/dashboard" className="hover:text-brg">Dashboard</Link>
              <Link href="/score" className="hover:text-brg">Score</Link>
              <Link href="/chat" className="hover:text-brg">Chat</Link>
              <Link href="/news" className="hover:text-brg">News</Link>
              <Link href="/portfolio" className="hover:text-brg">Portfolio</Link>
              <Link href="/investors" className="hover:text-brg">Investors</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-cream-300 bg-cream-50 py-4">
          <div className="mx-auto max-w-6xl px-6 text-xs text-ink-soft">
            Personal use · educational · not financial advice.
          </div>
        </footer>
      </body>
    </html>
  );
}
