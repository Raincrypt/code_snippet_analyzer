import { useEffect, useId, useRef, useState } from "react";
import { Monitor, Moon, Settings2, Sun } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { SegmentedControl, type SegmentedOption } from "@/components/ui/SegmentedControl";
import type { EditorFontSize, ReplyStyle, Settings, ThemePreference } from "@/types/settings";

const THEME_OPTIONS: readonly SegmentedOption<ThemePreference>[] = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  {
    value: "system",
    label: "System",
    Icon: Monitor,
    hint: "Follows your device and switches automatically.",
  },
];

const FONT_SIZE_OPTIONS: readonly SegmentedOption<EditorFontSize>[] = [
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
];

const REPLY_STYLE_OPTIONS: readonly SegmentedOption<ReplyStyle>[] = [
  { value: "brief", label: "Brief", hint: "Short, direct answers." },
  { value: "balanced", label: "Balanced", hint: "A clear explanation with the key fix." },
  { value: "detailed", label: "Detailed", hint: "Step-by-step reasoning with examples." },
];

type SettingsMenuProps = {
  settings: Settings;
  onChange: (patch: Partial<Settings>) => void;
};

export function SettingsMenu({ settings, onChange }: SettingsMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  // While open: close on outside click or Escape (Escape returns focus to the trigger).
  useEffect(() => {
    if (!open) return;
    function handlePointerDown(e: PointerEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    }
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <Button
        ref={triggerRef}
        variant="ghost"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        icon={<Settings2 className="size-4" aria-hidden />}
      >
        Settings
      </Button>

      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label="Settings"
          className="absolute top-full right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] space-y-5 rounded-lg border border-ink-700 bg-ink-900 p-4 shadow-xl"
        >
          <SegmentedControl
            legend="Theme"
            name="theme"
            value={settings.theme}
            options={THEME_OPTIONS}
            onChange={(theme) => onChange({ theme })}
          />
          <SegmentedControl
            legend="Editor font size"
            name="editor-font-size"
            value={settings.editorFontSize}
            options={FONT_SIZE_OPTIONS}
            onChange={(editorFontSize) => onChange({ editorFontSize })}
          />
          <SegmentedControl
            legend="Reply style"
            name="reply-style"
            value={settings.replyStyle}
            options={REPLY_STYLE_OPTIONS}
            onChange={(replyStyle) => onChange({ replyStyle })}
          />
          <p className="text-xs text-fg-muted">Saved on this device.</p>
        </div>
      )}
    </div>
  );
}
