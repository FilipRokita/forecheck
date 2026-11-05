type CardProps = {
  children: React.ReactNode;
  className?: string;
  as?: "div" | "section";
  /** Milliseconds before the entrance animation starts, so cards arrive one after another. */
  delay?: number;
  style?: React.CSSProperties;
};

export function Card({ children, className = "", as: Tag = "div", delay = 0, style }: CardProps) {
  return <Tag style={{ animationDelay: `${delay}ms`, ...style }} className={`min-w-0 animate-rise rounded-[14px] border border-border bg-surface p-5 transition-colors duration-200 hover:border-border-strong sm:p-6 ${className}`}>{children}</Tag>;
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
