import { useState } from "react";
import { FileSearch, Info, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Tabs, panelId, tabId, type TabItem } from "@/components/ui/Tabs";
import type { CodeIssue, ReviewResult, ReviewState } from "@/types/review";
import { ComplexityTab } from "./ComplexityTab";
import { FindingsTab } from "./FindingsTab";
import { Message } from "./Message";
import { MetricsTab } from "./MetricsTab";
import { OverviewTab, type TabId } from "./OverviewTab";
import { ReviewProgress } from "./ReviewProgress";
import { Section } from "./Section";

type ReviewPanelProps = {
  review: ReviewState;
  /** The code has been edited since this review was made. */
  stale: boolean;
  onAsk: (issue: CodeIssue) => void;
  onLocate: (issue: CodeIssue) => void;
  onLocateLines: (startLine: number, endLine: number) => void;
  activeKey: string | null;
  onRetry: () => void;
};

export function ReviewPanel({ review, stale, onRetry, ...rest }: ReviewPanelProps) {
  switch (review.status) {
    case "idle":
      return (
        <Message icon={<FileSearch className="size-6" />} title="Nothing reviewed yet">
          Paste code into the editor and choose Review. You will get a summary, findings with fixes,
          time complexity and any algorithms recognised.
        </Message>
      );
    case "loading":
      return <ReviewProgress stage={review.stage ?? null} />;
    case "error":
      return (
        <Message
          icon={<TriangleAlert className="size-6 text-sev-error" />}
          title="The review didn’t finish"
        >
          {review.message}
          <Button variant="ghost" className="mt-3" onClick={onRetry}>
            Try again
          </Button>
        </Message>
      );
    case "success":
      return <ResultView result={review.result} stale={stale} {...rest} />;
  }
}

type ResultViewProps = Omit<ReviewPanelProps, "review" | "onRetry"> & { result: ReviewResult };

function ResultView({ result, stale, onAsk, onLocate, onLocateLines, activeKey }: ResultViewProps) {
  const [tab, setTab] = useState<TabId>("overview");

  // When the editor selects a finding, show the Findings tab (adjusting state while rendering
  // is React's recommended way to react to a changed prop).
  const [seenKey, setSeenKey] = useState(activeKey);
  if (activeKey !== seenKey) {
    setSeenKey(activeKey);
    if (activeKey) setTab("findings");
  }

  const staleBanner = stale && (
    <p
      role="status"
      className="flex items-center gap-2 border-b border-sev-warning/40 bg-sev-warning/10 px-4 py-2 text-xs text-fg"
    >
      <Info className="size-4 shrink-0 text-sev-warning" aria-hidden />
      This review is for an earlier version of your code. Review again to update it.
    </p>
  );

  if (result.verdict === "not-assessed") {
    return (
      <div>
        {staleBanner}
        <div className="m-4 rounded-md border border-ink-700 bg-ink-900 p-4">
          <p className="text-sm font-semibold">Not analysed</p>
          <p className="mt-1 text-sm leading-relaxed text-fg-muted">{result.summary}</p>
        </div>
        <MetricsTab metrics={result.metrics} />
        {result.limitations.length > 0 && (
          <Section title="Limits of this review" className="px-4 pb-4">
            <ul className="list-disc space-y-1 pl-5 text-sm text-fg-muted">
              {result.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    );
  }

  const items: TabItem<TabId>[] = [
    { id: "overview", label: "Overview" },
    { id: "findings", label: "Findings", badge: result.issues.length },
    { id: "complexity", label: "Complexity" },
    { id: "metrics", label: "Metrics" },
  ];

  return (
    <div>
      <div className="sticky top-0 z-10 bg-ink-950">
        {staleBanner}
        <Tabs
          label="Review sections"
          idPrefix="review"
          items={items}
          value={tab}
          onChange={setTab}
        />
      </div>
      <div
        role="tabpanel"
        id={panelId("review", tab)}
        aria-labelledby={tabId("review", tab)}
        tabIndex={0}
      >
        {tab === "overview" && (
          <OverviewTab result={result} onLocate={onLocate} onOpenTab={setTab} />
        )}
        {tab === "findings" && (
          <FindingsTab
            issues={result.issues}
            priorityFixes={result.priorityFixes}
            activeKey={activeKey}
            onLocate={onLocate}
            onAsk={onAsk}
          />
        )}
        {tab === "complexity" && (
          <ComplexityTab
            complexity={result.complexity}
            algorithms={result.algorithms}
            onLocateLines={onLocateLines}
          />
        )}
        {tab === "metrics" && <MetricsTab metrics={result.metrics} />}
      </div>
    </div>
  );
}
