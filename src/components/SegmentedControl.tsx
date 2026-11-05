type Option = { id: string; label: string };

type Props = {
  label: string;
  options: readonly Option[];
  value: string;
  onChange: (id: string) => void;
  /** Scrolls sideways instead of wrapping, for a row that is too long for a phone. */
  scroll?: boolean;
};

export function SegmentedControl({ label, options, value, onChange, scroll = false }: Props) {
  return (
    <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-2.5">
      <span className="text-fg-muted max-sm:sr-only" id={`${label}-label`}>
        {label}
      </span>
      <div
        role="group"
        aria-labelledby={`${label}-label`}
        className={`flex gap-1 rounded-xl border border-border bg-surface p-1 ${scroll ? "overflow-x-auto" : ""}`}
      >
        {options.map((option) => {
          const selected = option.id === value;
          return (
            <button
              key={option.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(option.id)}
              className={`min-h-11 flex-none rounded-lg border px-4 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf sm:min-h-9 sm:px-3.5 ${
                selected
                  ? "border-border-strong bg-surface-raised font-medium text-white shadow-[0_1px_8px_color-mix(in_srgb,var(--color-model-ecmwf)_14%,transparent)]"
                  : "border-transparent text-fg-muted hover:bg-surface-raised/60 hover:text-fg"
              } ${scroll ? "" : "flex-1 sm:flex-none"}`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
