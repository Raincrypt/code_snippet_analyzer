import type { ReactNode } from "react";

/** A centred notice used for empty, error and "nothing found" states. */
export function Message({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-sm flex-col items-center justify-center gap-2 py-10 text-center">
      <div className="text-fg-muted">{icon}</div>
      <h3 className="font-semibold text-fg">{title}</h3>
      <div className="flex flex-col items-center text-sm leading-relaxed text-fg-muted">
        {children}
      </div>
    </div>
  );
}
