"use client";

import Link from "next/link";

/** The logo from the README: the app icon and a two-tone wordmark. Pressing it scrolls smoothly back to the top. */
export function Logo() {
  const toTop = (event: React.MouseEvent) => {
    event.preventDefault();
    const reduced = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
  };

  return (
    <Link
      href="/"
      onClick={toTop}
      className="group flex items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-model-ecmwf"
    >
      <svg width="30" height="30" viewBox="0 0 32 32" fill="none" aria-hidden="true" className="flex-none">
        <rect x="0.5" y="0.5" width="31" height="31" rx="7.5" className="fill-surface stroke-border-strong" />
        <path d="M8 17l5.5 5L24 10" stroke="var(--color-model-ecmwf)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="text-[22px] font-bold leading-none tracking-[-0.03em] text-fg">
        Fore<span className="font-medium text-fg-muted transition-colors group-hover:text-fg">check</span>
      </span>
    </Link>
  );
}
