"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function Nav() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <nav className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3" aria-label="Primary">
        <Link href="/" className="font-semibold">
          Research Agent
        </Link>
        <Link href="/runs" className="text-sm underline-offset-4 hover:underline">
          Runs
        </Link>
        <Link href="/memory" className="text-sm underline-offset-4 hover:underline">
          Memory
        </Link>
        <Link href="/settings" className="text-sm underline-offset-4 hover:underline">
          Settings
        </Link>
        <button
          type="button"
          className="ml-auto rounded border px-2 py-1 text-sm"
          onClick={() => setDark((value) => !value)}
        >
          {dark ? "Light" : "Dark"}
        </button>
      </nav>
    </header>
  );
}
