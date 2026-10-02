import { z } from "zod";

export const ThemePreferenceSchema = z.enum(["light", "dark", "system"]);
export const EditorFontSizeSchema = z.enum(["small", "medium", "large"]);
export const ReplyStyleSchema = z.enum(["brief", "balanced", "detailed"]);

// `.catch(default)` makes each field fall back on its own, so one bad or missing
// value in storage never discards the user's other settings.
export const SettingsSchema = z.object({
  theme: ThemePreferenceSchema.catch("system"),
  editorFontSize: EditorFontSizeSchema.catch("medium"),
  replyStyle: ReplyStyleSchema.catch("balanced"),
});

export type ThemePreference = z.infer<typeof ThemePreferenceSchema>;
export type EditorFontSize = z.infer<typeof EditorFontSizeSchema>;
export type ReplyStyle = z.infer<typeof ReplyStyleSchema>;
export type Settings = z.infer<typeof SettingsSchema>;

export const DEFAULT_SETTINGS: Settings = {
  theme: "system",
  editorFontSize: "medium",
  replyStyle: "balanced",
};
