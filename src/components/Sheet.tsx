"use client";

import { useEffect, useRef } from "react";

type Props = {
  title: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
};

/**
 * A modal window that slides up from the bottom of a phone like a drawer, and is a centred window on a larger screen.
 * It is a native dialog: focus is held inside, Escape closes it, and the focus goes back to what opened it.
 * The parent owns `open`. The content is only rendered while it is open.
 */
export function Sheet({ title, open, onClose, children }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  // The listeners below are added once, so they call whichever `onClose` is the latest.
  const close = useRef(onClose);
  useEffect(() => {
    close.current = onClose;
  });

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    // A press on the backdrop lands on the dialog element itself, not on its content. It counts only if it also began there,
    // so selecting text and letting go over the backdrop does not close the window.
    let startedOnBackdrop = false;
    const remember = (event: PointerEvent) => {
      startedOnBackdrop = event.target === element;
    };
    const closeOnBackdrop = (event: MouseEvent) => {
      if (startedOnBackdrop && event.target === element) close.current();
    };
    // Escape closes the dialog by itself: the parent is told so its `open` follows.
    const closed = () => close.current();
    element.addEventListener("pointerdown", remember);
    element.addEventListener("click", closeOnBackdrop);
    element.addEventListener("close", closed);
    return () => {
      element.removeEventListener("pointerdown", remember);
      element.removeEventListener("click", closeOnBackdrop);
      element.removeEventListener("close", closed);
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-label={title}
      className="m-0 mt-auto max-h-[93dvh] w-full max-w-none overflow-hidden rounded-t-2xl border border-b-0 border-border bg-surface p-0 text-fg shadow-2xl shadow-black/60 backdrop:bg-black/70 backdrop:backdrop-blur-sm max-sm:open:animate-drawer sm:m-auto sm:max-h-[85dvh] sm:max-w-lg sm:rounded-2xl sm:border-b sm:open:animate-fade"
    >
      {open ? (
        <>
          <div aria-hidden="true" className="mx-auto mt-2 h-1 w-10 rounded-full bg-border-strong sm:hidden" />
          <div className="flex items-center justify-between border-b border-border px-5 py-2">
            <h2 className="text-base font-semibold">{title}</h2>
            <button
              type="button"
              aria-label="Close"
              onClick={onClose}
              className="grid size-11 place-items-center rounded-lg text-fg-muted hover:bg-surface-raised hover:text-fg focus-visible:outline-2 focus-visible:outline-model-ecmwf sm:size-9"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
                <path d="M2.5 2.5l9 9M11.5 2.5l-9 9" />
              </svg>
            </button>
          </div>
          <div className="max-h-[calc(93dvh-5.5rem)] overflow-y-auto overscroll-contain px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:max-h-[calc(85dvh-4rem)]">{children}</div>
        </>
      ) : null}
    </dialog>
  );
}
