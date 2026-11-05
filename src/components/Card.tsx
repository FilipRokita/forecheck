export function Card({ children, className = "", as: Tag = "div" }: { children: React.ReactNode; className?: string; as?: "div" | "section" }) {
  return <Tag className={`min-w-0 animate-rise rounded-[14px] border border-border bg-surface p-5 transition-colors duration-200 hover:border-border-strong sm:p-6 ${className}`}>{children}</Tag>;
}

export function CardTitle({ children, id }: { children: React.ReactNode; id?: string }) {
  return (
    <h2 id={id} className="text-base font-semibold">
      {children}
    </h2>
  );
}

export function CardSubtitle({ children }: { children: React.ReactNode }) {
  return <p className="mt-0.5 text-fg-muted">{children}</p>;
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return <div className="text-xs uppercase tracking-[0.06em] text-fg-muted">{children}</div>;
}
