import { z } from "zod";
import { REVIEW_STAGES, ReviewResultSchema } from "@/types/review";
import { readSse } from "./sse";
import { ApiError, type ReviewApi } from "./types";

const ReviewDetailSchema = z.object({ id: z.string().min(1), result: ReviewResultSchema });
const StageEventSchema = z.object({ stage: z.enum(REVIEW_STAGES) });
const ErrorEventSchema = z.object({ message: z.string(), requestId: z.string().nullish() });
const ErrorBodySchema = z.object({ error: ErrorEventSchema });
const ExchangeSchema = z.object({ assistantMessage: z.object({ content: z.string() }) });
const HealthSchema = z.object({ reviewer: z.string(), model: z.string().nullish() });

const ModelStatusSchema = z.object({
  state: z.enum(["ready", "model-missing", "unreachable"]),
  detail: z.string(),
});

export type ModelStatus = z.infer<typeof ModelStatusSchema>;

export type HttpApi = ReviewApi & {
  health(signal?: AbortSignal): Promise<{ reviewer: string; model?: string | null }>;
  /** Whether the AI model can take a review right now. */
  modelStatus(signal?: AbortSignal): Promise<ModelStatus>;
};

type Options = { baseUrl?: string; fetchImpl?: typeof fetch };

const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

function withReference(message: string, requestId: string | null | undefined, status: number) {
  // A short reference helps when reporting a server-side problem; it is noise for user mistakes.
  return status >= 500 && requestId ? `${message} (ref ${requestId.slice(0, 8)})` : message;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  try {
    const parsed = ErrorBodySchema.safeParse(await response.json());
    if (parsed.success) {
      const { message, requestId } = parsed.data.error;
      return new ApiError(withReference(message, requestId, response.status));
    }
  } catch {
    // Not JSON (for example a proxy error page): fall through to a generic message.
  }
  if (response.status === 429)
    return new ApiError("Too many requests. Wait a moment and try again.");
  if (response.status >= 500)
    return new ApiError("The server had a problem. Try again in a moment.");
  return new ApiError(`The request failed (${response.status}).`);
}

export function createHttpApi({ baseUrl = "/api", fetchImpl }: Options = {}): HttpApi {
  // Wrapped so `fetch` is always called as a plain function (calling it as a method throws).
  const doFetch: typeof fetch = fetchImpl ?? ((input, init) => fetch(input, init));

  async function send(path: string, init: RequestInit): Promise<Response> {
    let response: Response;
    try {
      response = await doFetch(`${baseUrl}${path}`, init);
    } catch (error) {
      if (isAbort(error) || init.signal?.aborted) throw error;
      throw new ApiError("Can't reach the server. Check your connection and try again.");
    }
    if (!response.ok) throw await errorFromResponse(response);
    return response;
  }

  const json = (body: unknown): RequestInit => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return {
    async review(request, signal, onProgress) {
      const response = await send("/reviews/stream", {
        ...json({ code: request.code, language: request.language }),
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        signal,
      });
      if (!response.body) throw new ApiError("The server sent no data. Try again.");

      for await (const { event, data } of readSse(response.body)) {
        let payload: unknown;
        try {
          payload = JSON.parse(data);
        } catch {
          throw new ApiError("The server sent something unreadable. Try again.");
        }
        if (event === "stage") {
          const stage = StageEventSchema.safeParse(payload);
          if (stage.success) onProgress?.(stage.data.stage);
        } else if (event === "result") {
          const detail = ReviewDetailSchema.safeParse(payload);
          if (!detail.success) {
            throw new ApiError("The server sent a review in an unexpected format.");
          }
          return { id: detail.data.id, result: detail.data.result };
        } else if (event === "error") {
          const error = ErrorEventSchema.safeParse(payload);
          throw new ApiError(
            error.success
              ? withReference(error.data.message, error.data.requestId, 500)
              : "The review failed. Try again.",
          );
        }
      }
      throw new ApiError("The review ended unexpectedly. Try again.");
    },

    async ask({ reviewId, question, replyStyle }, signal) {
      const response = await send(`/reviews/${encodeURIComponent(reviewId)}/messages`, {
        ...json({ question, replyStyle }),
        signal,
      });
      const parsed = ExchangeSchema.safeParse(await response.json());
      if (!parsed.success) throw new ApiError("The server sent a reply in an unexpected format.");
      return parsed.data.assistantMessage.content;
    },

    async health(signal) {
      const response = await send("/health", { signal });
      const parsed = HealthSchema.safeParse(await response.json());
      if (!parsed.success) throw new ApiError("Unexpected response from the server.");
      return parsed.data;
    },

    async modelStatus(signal) {
      const response = await send("/reviewer/status", { signal });
      const parsed = ModelStatusSchema.safeParse(await response.json());
      if (!parsed.success) throw new ApiError("Unexpected response from the server.");
      return parsed.data;
    },
  };
}
