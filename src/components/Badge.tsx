export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full border border-warn-border bg-warn-bg px-3 py-1 text-xs text-warn">{children}</span>
  );
}
