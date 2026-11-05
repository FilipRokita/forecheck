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
      className="group flex items-center gap-1.5 rounded-lg sm:gap-2.5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-model-ecmwf"
    >
      <svg width="30" height="30" viewBox="0 0 32 32" fill="none" aria-hidden="true" className="size-6 flex-none text-fg min-[381px]:size-7 sm:size-[30px]">
        <rect x="0.5" y="0.5" width="31" height="31" rx="7.5" className="fill-surface stroke-border-strong" />
        <g transform="translate(0 .5)" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10 23.5a5 5 0 0 1-.5-9.97 7 7 0 0 1 13.3-1.5A5.5 5.5 0 0 1 22.5 23.5H10z" />
          <path d="M12.9 17.3l2.4 2.4 4.2-4.6" />
        </g>
      </svg>
      <span className="text-lg font-bold min-[381px]:text-xl sm:text-[22px] leading-none tracking-[-0.03em] text-fg">
        Fore<span className="font-medium text-fg-muted transition-colors group-hover:text-fg">check</span>
      </span>
    </Link>
  );
}
