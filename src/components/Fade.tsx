/** Text that fades in again whenever `id` changes, so words change as smoothly as the numbers beside them. */
export function Fade({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <span key={id} className="animate-fade">
      {children}
    </span>
  );
}
