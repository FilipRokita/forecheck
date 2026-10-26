import { modelColor } from "@/lib/models";

/** A model's name with its colour as a small square. The name is always there, so colour never carries the meaning alone. */
export function ModelName({ id, label, className = "" }: { id: string; label: string; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span aria-hidden="true" className="inline-block size-2.5 flex-none rounded-[3px]" style={{ background: modelColor(id) }} />
      {label}
    </span>
  );
}
