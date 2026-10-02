/*
 * This is the ARIA "window splitter" pattern: a focusable role="separator" with aria-value*
 * attributes is an interactive widget. jsx-a11y classifies separator as non-interactive, so the
 * two rules below are disabled for this file only.
 */
/* eslint-disable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */
import { useRef, type KeyboardEvent, type PointerEvent } from "react";

type ResizeHandleProps = {
  /** "x": a vertical bar that changes a width. "y": a horizontal bar that changes a height. */
  axis: "x" | "y";
  label: string;
  /** Size of the panel that grows when the handle moves toward the start (left / up). */
  value: number;
  min: number;
  /** Evaluated when a drag starts, so it can depend on the current container size. */
  max: () => number;
  onChange: (value: number) => void;
  className?: string;
};

const STEP = 16;
const BIG_STEP = 64;

const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max);

export function ResizeHandle({
  axis,
  label,
  value,
  min,
  max,
  onChange,
  className = "",
}: ResizeHandleProps) {
  const drag = useRef<{ start: number; startValue: number; max: number } | null>(null);
  const pointerPos = (e: PointerEvent) => (axis === "x" ? e.clientX : e.clientY);

  function handlePointerDown(e: PointerEvent<HTMLDivElement>) {
    e.currentTarget.setPointerCapture?.(e.pointerId);
    drag.current = { start: pointerPos(e), startValue: value, max: max() };
  }

  function handlePointerMove(e: PointerEvent<HTMLDivElement>) {
    const d = drag.current;
    if (!d) return;
    // Moving toward the start grows the panel, so subtract the pointer travel.
    onChange(clamp(d.startValue - (pointerPos(e) - d.start), min, d.max));
  }

  function handlePointerEnd(e: PointerEvent<HTMLDivElement>) {
    drag.current = null;
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const grow = axis === "x" ? "ArrowLeft" : "ArrowUp";
    const shrink = axis === "x" ? "ArrowRight" : "ArrowDown";
    const step = e.shiftKey ? BIG_STEP : STEP;
    let next: number | undefined;
    if (e.key === grow) next = value + step;
    else if (e.key === shrink) next = value - step;
    else if (e.key === "Home") next = min;
    else if (e.key === "End") next = max();
    if (next === undefined) return;
    e.preventDefault();
    onChange(clamp(next, min, max()));
  }

  const isX = axis === "x";
  return (
    <div
      role="separator"
      aria-orientation={isX ? "vertical" : "horizontal"}
      aria-label={label}
      aria-valuenow={Math.round(value)}
      aria-valuemin={min}
      aria-valuemax={Math.round(max())}
      tabIndex={0}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onKeyDown={handleKeyDown}
      className={`group flex shrink-0 touch-none items-center justify-center ${
        isX ? "w-1.5 cursor-col-resize" : "h-1.5 cursor-row-resize"
      } ${className}`}
    >
      <span
        aria-hidden
        className={`bg-ink-700 transition-colors group-hover:bg-sev-info group-focus-visible:bg-sev-info ${
          isX ? "h-full w-px group-hover:w-0.5" : "h-px w-full group-hover:h-0.5"
        }`}
      />
    </div>
  );
}
