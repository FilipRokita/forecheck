import type { Loadable } from "@/lib/api/use-api";

type Props<T> = {
  state: Loadable<T>;
  children: (data: T) => React.ReactNode;
  /** The size the content will have, so the page does not jump when it arrives. */
  skeletonClassName?: string;
  label: string;
};

/** Shows a placeholder while loading and a retry button when the request failed. */
export function Async<T>({ state, children, skeletonClassName = "h-40", label }: Props<T>) {
  if (state.status === "loading") {
    return (
      <div role="status" aria-label={`Loading ${label}`} className={`skeleton rounded-[14px] border border-border ${skeletonClassName}`} />
    );
  }
  if (state.status === "error") {
    return (
      <div role="alert" className="rounded-[14px] border border-border bg-surface p-5 sm:p-6">
        <p className="font-medium">Could not load {label}.</p>
        <p className="mt-1 text-fg-muted">{state.error.message}. The data may be updating, so try again in a moment.</p>
        <button type="button" onClick={state.retry} className="mt-3 min-h-11 rounded-lg border border-border-strong px-4 hover:bg-surface-raised focus-visible:outline-2 focus-visible:outline-model-ecmwf">
          Try again
        </button>
      </div>
    );
  }
  return <>{children(state.data)}</>;
}
