export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full border border-warn-border bg-warn-bg px-2.5 py-1 sm:px-3 text-xs text-warn">{children}</span>
  );
}
