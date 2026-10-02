import type { Extension } from "@codemirror/state";
import type { LanguageValue } from "@/utils/languages";

// Each language pack is a separate chunk, downloaded the first time that language is used.
const LOADERS: Record<LanguageValue, () => Promise<Extension>> = {
  javascript: async () => (await import("@codemirror/lang-javascript")).javascript(),
  typescript: async () =>
    (await import("@codemirror/lang-javascript")).javascript({ typescript: true }),
  python: async () => (await import("@codemirror/lang-python")).python(),
  go: async () => (await import("@codemirror/lang-go")).go(),
  rust: async () => (await import("@codemirror/lang-rust")).rust(),
  java: async () => (await import("@codemirror/lang-java")).java(),
};

const cache = new Map<string, Promise<Extension>>();

/** Resolves to the language support for `value`, or plain text (no extension) if unknown. */
export function loadLanguage(value: string): Promise<Extension> {
  const loader = LOADERS[value as LanguageValue];
  if (!loader) return Promise.resolve([]);
  let pending = cache.get(value);
  if (!pending) {
    pending = loader();
    cache.set(value, pending);
  }
  return pending;
}
