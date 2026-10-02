import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { hasError: boolean };

/** Catches render errors so one broken component never leaves a blank page. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div role="alert" className="grid h-dvh place-items-center p-6 text-center">
        <div className="max-w-sm space-y-3">
          <h1 className="text-lg font-semibold">Something broke</h1>
          <p className="text-sm text-fg-muted">
            The app hit an unexpected error. Reloading usually fixes it, and your pasted code is not
            saved anywhere.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="h-9 rounded-md bg-chalk px-3.5 text-sm font-semibold text-chalk-ink"
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}
