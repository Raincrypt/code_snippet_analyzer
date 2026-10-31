import { MOCK_REVIEW } from "@/mocks/review";
import { createHttpApi } from "./httpApi";
import { ApiError } from "./types";

const event = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

const sse = (...events: string[]) =>
  new Response(events.join(""), { headers: { "Content-Type": "text/event-stream" } });

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const request = { code: "x = 1", language: "python" };
const resultEvent = event("result", { id: "r1", result: MOCK_REVIEW });

function setup(respond: () => Response | Promise<Response>) {
  const fetchImpl = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(
    async () => respond(),
  );
  return { fetchImpl, api: createHttpApi({ fetchImpl: fetchImpl as unknown as typeof fetch }) };
}

describe("createHttpApi.review", () => {
  it("posts the code to the streaming endpoint", async () => {
    const { api, fetchImpl } = setup(() => sse(resultEvent));
    await api.review(request);
    const [url, init] = fetchImpl.mock.calls[0]!;
    expect(url).toBe("/api/reviews/stream");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual(request);
    expect(new Headers(init?.headers).get("accept")).toBe("text/event-stream");
  });

  it("reports each step as it arrives, then returns the saved review", async () => {
    const { api } = setup(() =>
      sse(event("stage", { stage: "prepare" }), event("stage", { stage: "analyse" }), resultEvent),
    );
    const onProgress = vi.fn();
    const response = await api.review(request, undefined, onProgress);
    expect(onProgress.mock.calls.map(([stage]) => stage)).toEqual(["prepare", "analyse"]);
    expect(response.id).toBe("r1");
    expect(response.result.complexity?.time).toBe("O(n²)");
  });

  it("ignores steps and events it does not know", async () => {
    const { api } = setup(() =>
      sse(event("stage", { stage: "daydream" }), event("mystery", { a: 1 }), resultEvent),
    );
    const onProgress = vi.fn();
    await expect(api.review(request, undefined, onProgress)).resolves.toMatchObject({ id: "r1" });
    expect(onProgress).not.toHaveBeenCalled();
  });

  it("turns an error event into an error with its message", async () => {
    const { api } = setup(() =>
      sse(
        event("error", {
          code: "reviewer_failed",
          message: "The reviewer could not complete the review.",
          requestId: "abcdef1234567",
        }),
      ),
    );
    await expect(api.review(request)).rejects.toThrow(
      "The reviewer could not complete the review. (ref abcdef12)",
    );
  });

  it("fails clearly when the stream ends without a result", async () => {
    const { api } = setup(() => sse(event("stage", { stage: "prepare" })));
    await expect(api.review(request)).rejects.toThrow("ended unexpectedly");
  });

  it("rejects a review that does not match the expected format", async () => {
    const { api } = setup(() => sse(event("result", { id: "r1", result: { nonsense: true } })));
    await expect(api.review(request)).rejects.toThrow("unexpected format");
  });

  it("rejects data that is not JSON", async () => {
    const { api } = setup(() => sse("event: result\ndata: not json\n\n"));
    await expect(api.review(request)).rejects.toThrow("unreadable");
  });

  it("uses the server's message for a refused request", async () => {
    const { api } = setup(() =>
      json(
        {
          error: {
            code: "payload_too_large",
            message: "Code is too long (maximum 100000 characters).",
            requestId: "r",
          },
        },
        413,
      ),
    );
    await expect(api.review(request)).rejects.toThrow(
      "Code is too long (maximum 100000 characters).",
    );
  });

  it("adds a reference to server errors only", async () => {
    const { api } = setup(() =>
      json(
        {
          error: {
            code: "internal_error",
            message: "Something went wrong on our side.",
            requestId: "0123456789abcdef",
          },
        },
        500,
      ),
    );
    await expect(api.review(request)).rejects.toThrow(
      "Something went wrong on our side. (ref 01234567)",
    );
  });

  it("gives a plain message for a server error without a JSON body", async () => {
    const { api } = setup(() => new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(api.review(request)).rejects.toThrow("The server had a problem");
  });

  it("explains rate limiting", async () => {
    const { api } = setup(() => new Response("", { status: 429 }));
    await expect(api.review(request)).rejects.toThrow("Too many requests");
  });

  it("explains when the server cannot be reached", async () => {
    const { api } = setup(() => Promise.reject(new TypeError("Failed to fetch")));
    const error = await api.review(request).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as Error).message).toContain("Can't reach the server");
  });

  it("lets a cancelled request through unchanged, so callers can tell it was cancelled", async () => {
    const abort = new DOMException("Aborted", "AbortError");
    const { api } = setup(() => Promise.reject(abort));
    await expect(api.review(request)).rejects.toBe(abort);
  });
});

describe("createHttpApi.ask", () => {
  const exchange = { userMessage: { content: "Why?" }, assistantMessage: { content: "Because." } };

  it("posts the question to the review's messages and returns the reply", async () => {
    const { api, fetchImpl } = setup(() => json(exchange, 201));
    const reply = await api.ask({ reviewId: "r 1/2", question: "Why?", replyStyle: "brief" });
    expect(reply).toBe("Because.");
    const [url, init] = fetchImpl.mock.calls[0]!;
    expect(url).toBe("/api/reviews/r%201%2F2/messages");
    expect(JSON.parse(init?.body as string)).toEqual({ question: "Why?", replyStyle: "brief" });
  });

  it("reports a problem with the review", async () => {
    const { api } = setup(() =>
      json({ error: { code: "not_found", message: "Review not found.", requestId: "r" } }, 404),
    );
    await expect(
      api.ask({ reviewId: "gone", question: "Why?", replyStyle: "brief" }),
    ).rejects.toThrow("Review not found.");
  });

  it("rejects a reply in an unexpected format", async () => {
    const { api } = setup(() => json({ hello: "world" }, 201));
    await expect(
      api.ask({ reviewId: "r1", question: "Why?", replyStyle: "brief" }),
    ).rejects.toThrow("unexpected format");
  });
});

describe("createHttpApi.health", () => {
  it("reports which reviewer the backend uses", async () => {
    const { api, fetchImpl } = setup(() =>
      json({ status: "ok", version: "0.1.0", reviewer: "stub" }),
    );
    await expect(api.health()).resolves.toEqual({ reviewer: "stub" });
    expect(fetchImpl.mock.calls[0]![0]).toBe("/api/health");
  });
});

describe("createHttpApi.modelStatus", () => {
  it("reads whether the model can take a review", async () => {
    const { api, fetchImpl } = setup(() =>
      json({ ready: true, state: "ready", model: "m", detail: "Ready." }),
    );
    await expect(api.modelStatus()).resolves.toEqual({ state: "ready", detail: "Ready." });
    expect(fetchImpl.mock.calls[0]![0]).toBe("/api/reviewer/status");
  });

  it("rejects an answer it does not understand", async () => {
    const { api } = setup(() => json({ ready: true }));
    await expect(api.modelStatus()).rejects.toBeInstanceOf(ApiError);
  });
});
