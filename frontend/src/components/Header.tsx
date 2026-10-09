import type { Settings } from "@/types/settings";
import { SettingsMenu } from "./SettingsMenu";

type HeaderProps = {
  settings: Settings;
  onSettingsChange: (patch: Partial<Settings>) => void;
};

export function Header({ settings, onSettingsChange }: HeaderProps) {
  return (
    <header className="relative z-30 flex h-14 shrink-0 items-center gap-3 border-b border-ink-700 bg-ink-900/80 px-4 backdrop-blur-md">
      <svg
        viewBox="0 0 24 24"
        className="size-6 shrink-0 text-chalk"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        aria-hidden
      >
        <path d="M8 5 4 12l4 7" />
        <path d="M13 8h7M13 12h5M13 16h7" />
      </svg>
      <h1 className="min-w-0 truncate text-[1.05rem] font-semibold tracking-tight">
        Code Snippet Analyzer
      </h1>
      <nav aria-label="App" className="ml-auto flex shrink-0 items-center gap-1">
        <SettingsMenu settings={settings} onChange={onSettingsChange} />
      </nav>
    </header>
  );
}
