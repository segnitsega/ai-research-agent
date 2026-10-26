"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { cn } from "@/lib/format";
import { applyTheme, readPrefs, writePrefs } from "@/lib/prefs";

const LINKS = [
  { href: "/", label: "Desk", hint: "New question" },
  { href: "/runs", label: "Runs", hint: "History" },
  { href: "/memory", label: "Memory", hint: "What it keeps" },
  { href: "/settings", label: "Settings", hint: "Theme and models" },
];

function Mark() {
  return (
    <svg viewBox="0 0 36 36" className="h-9 w-9" aria-hidden>
      <rect x="4" y="5" width="20" height="26" rx="3" fill="currentColor" className="text-accent" />
      <path d="M18 5h8.5L32 10.5V31a3 3 0 0 1-3 3H18" className="text-copper" fill="currentColor" />
      <path d="M26.5 5.5V11H32" fill="none" stroke="var(--paper)" strokeWidth="1.4" />
    </svg>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    applyTheme(readPrefs().theme);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () => {
      if (readPrefs().theme === "system") applyTheme("system");
    };
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  return (
    <div className="min-h-screen">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-paper"
      >
        Skip to content
      </a>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[var(--sidebar)] flex-col border-r border-line bg-raised/80 px-4 py-6 backdrop-blur-md lg:flex">
        <Link href="/" className="flex items-center gap-3 rounded-2xl px-2 py-1">
          <Mark />
          <span>
            <span className="block font-display text-xl leading-none">Research Agent</span>
            <span className="mt-1 block text-xs text-muted">A reading desk</span>
          </span>
        </Link>
        <nav className="mt-10 flex flex-1 flex-col gap-1" aria-label="Primary">
          {LINKS.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-2xl px-3 py-3 transition",
                  active ? "bg-accent-soft text-ink" : "text-muted hover:bg-paper hover:text-ink",
                )}
              >
                <span className="block text-sm font-semibold">{link.label}</span>
                <span className="block text-xs">{link.hint}</span>
              </Link>
            );
          })}
        </nav>
        <p className="px-3 text-xs leading-5 text-muted">Quotes are checked against the page before they can be cited.</p>
      </aside>
      <div className="lg:pl-[var(--sidebar)]">
        <header className="sticky top-0 z-20 border-b border-line bg-paper/85 backdrop-blur-md lg:hidden">
          <div className="flex items-center gap-3 px-4 py-3">
            <Mark />
            <span className="font-display text-lg">Research Agent</span>
          </div>
          <nav className="flex gap-2 overflow-x-auto px-4 pb-3" aria-label="Primary">
            {LINKS.map((link) => {
              const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "min-h-11 rounded-full px-4 py-2 text-sm font-semibold",
                    active ? "bg-ink text-paper" : "bg-raised text-muted",
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main id="content" className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}

export function ThemeButton() {
  return (
    <button
      type="button"
      className="min-h-11 rounded-full border border-line bg-raised px-4 text-sm font-semibold"
      onClick={() => {
        const next = document.documentElement.classList.contains("dark") ? "light" : "dark";
        writePrefs({ ...readPrefs(), theme: next });
      }}
    >
      <span className="show-in-dark">Light</span>
      <span className="show-in-light">Dark</span>
    </button>
  );
}
