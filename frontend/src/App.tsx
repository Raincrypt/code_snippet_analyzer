import { useMemo, useRef, useState, type CSSProperties } from "react";
import { createMockApi, type MockOutcome } from "@/api/mockApi";
import { Header } from "@/components/Header";
import { ResizeHandle } from "@/components/ResizeHandle";
import { StatusBar } from "@/components/StatusBar";
import { ChatPanel } from "@/features/chat/ChatPanel";
import { CodeEditor, type CodeEditorHandle } from "@/features/review/CodeEditor";
import { ResultsSection } from "@/features/review/ResultsSection";
import { useChat } from "@/hooks/useChat";
import { usePersistentNumber } from "@/hooks/usePersistentNumber";
import { useReview } from "@/hooks/useReview";
import { useSettings } from "@/hooks/useSettings";
import { useApplyTheme } from "@/hooks/useTheme";
import { SAMPLE_CODE } from "@/mocks/review";
import type { CodeIssue } from "@/types/review";
import { findIssueAtLine, issueKey } from "@/utils/issues";
import { formatLineRange } from "@/utils/severity";

// Layout limits (px). The editor never shrinks below MIN_EDITOR_* so it stays usable.
const MIN_CHAT_WIDTH = 320;
const MIN_LEFT_WIDTH = 360;
const MIN_RESULTS_HEIGHT = 160;
const MIN_EDITOR_HEIGHT = 200;
const HANDLE_SIZE = 6;

export default function App() {
  const [code, setCode] = useState(SAMPLE_CODE);
  const [language, setLanguage] = useState("javascript");
  const [outcome, setOutcome] = useState<MockOutcome>("issues");
  const [settings, updateSettings] = useSettings();
  useApplyTheme(settings.theme);

  // The review panel starts minimized and is only opened by the user.
  const [resultsOpen, setResultsOpen] = useState(false);
  const [chatWidth, setChatWidth] = usePersistentNumber("code-snippet-analyzer:chat-width", 400);
  const [resultsHeight, setResultsHeight] = usePersistentNumber(
    "code-snippet-analyzer:results-height",
    320,
  );

  const mainRef = useRef<HTMLElement>(null);
  const leftRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);
  const editorRef = useRef<CodeEditorHandle>(null);
  // The finding currently selected (from a card or from the editor gutter).
  const [activeKey, setActiveKey] = useState<string | null>(null);

  // Swap createMockApi for an HTTP client once the backend exists; nothing else changes.
  const api = useMemo(() => createMockApi({ outcome }), [outcome]);
  const review = useReview(api);
  const chat = useChat(api, settings.replyStyle);

  function runReview() {
    if (!code.trim()) return;
    setActiveKey(null);
    void review.run({ code, language });
  }

  // Card -> editor: select and scroll to the finding's lines.
  function locateIssue(issue: CodeIssue) {
    setActiveKey(issueKey(issue));
    editorRef.current?.revealLines(issue.line, issue.endLine);
  }

  // Editor gutter -> card: open the results panel and highlight the matching card.
  function handleGutterClick(line: number) {
    if (review.state.status !== "success") return;
    const issue = findIssueAtLine(review.state.result.issues, line);
    if (!issue) return;
    setResultsOpen(true);
    setActiveKey(issueKey(issue));
  }

  function askAbout(issue: CodeIssue) {
    const where = formatLineRange(issue.line, issue.endLine).toLowerCase();
    chat.setDraft(`About ${where} (${issue.title}): `);
    chatInputRef.current?.focus();
  }

  const maxChatWidth = () =>
    Math.max(MIN_CHAT_WIDTH, (mainRef.current?.clientWidth ?? 1200) - MIN_LEFT_WIDTH - HANDLE_SIZE);
  const maxResultsHeight = () =>
    Math.max(
      MIN_RESULTS_HEIGHT,
      (leftRef.current?.clientHeight ?? 800) - MIN_EDITOR_HEIGHT - HANDLE_SIZE,
    );

  // Memoized so the editor is only updated when the findings actually change.
  const editorIssues = useMemo(
    () =>
      review.state.status === "success"
        ? review.state.result.issues.map(({ line, endLine, severity }) => ({
            line,
            endLine,
            severity,
          }))
        : [],
    [review.state],
  );

  return (
    <div className="flex h-dvh flex-col">
      <Header settings={settings} onSettingsChange={updateSettings} />
      <main
        ref={mainRef}
        style={{ "--chat-w": `${chatWidth}px` } as CSSProperties}
        className="grid min-h-0 flex-1 overflow-y-auto lg:grid-cols-[minmax(0,1fr)_auto_min(var(--chat-w),60vw)] lg:overflow-hidden"
      >
        <div ref={leftRef} className="flex min-h-0 min-w-0 flex-col">
          <div className="flex min-h-[340px] flex-1 flex-col lg:min-h-[200px]">
            <CodeEditor
              ref={editorRef}
              code={code}
              onCodeChange={setCode}
              language={language}
              onLanguageChange={setLanguage}
              onReview={runReview}
              loading={review.state.status === "loading"}
              issues={editorIssues}
              fontSize={settings.editorFontSize}
              onIssueClick={handleGutterClick}
            />
          </div>
          {resultsOpen && (
            <ResizeHandle
              axis="y"
              label="Resize review panel"
              value={resultsHeight}
              min={MIN_RESULTS_HEIGHT}
              max={maxResultsHeight}
              onChange={setResultsHeight}
              className="hidden lg:flex"
            />
          )}
          <ResultsSection
            review={review.state}
            open={resultsOpen}
            onToggle={() => setResultsOpen((open) => !open)}
            height={resultsHeight}
            onAsk={askAbout}
            onLocate={locateIssue}
            activeKey={activeKey}
            onRetry={runReview}
          />
        </div>

        <ResizeHandle
          axis="x"
          label="Resize chat panel"
          value={chatWidth}
          min={MIN_CHAT_WIDTH}
          max={maxChatWidth}
          onChange={setChatWidth}
          className="hidden lg:flex"
        />

        <div className="flex min-h-[420px] min-w-0 flex-col border-t border-ink-700 lg:min-h-0 lg:border-t-0">
          <ChatPanel
            messages={chat.messages}
            thinking={chat.thinking}
            error={chat.error}
            draft={chat.draft}
            onDraftChange={chat.setDraft}
            onSend={() => void chat.send()}
            onClear={chat.clear}
            inputRef={chatInputRef}
          />
        </div>
      </main>
      <StatusBar status={review.state.status} outcome={outcome} onOutcomeChange={setOutcome} />
    </div>
  );
}
