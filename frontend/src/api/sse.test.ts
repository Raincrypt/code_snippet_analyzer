import { readSse, type SseMessage } from "./sse";

/** A response body that delivers the given chunks one at a time. */
function bodyOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>): Promise<SseMessage[]> {
  const messages: SseMessage[] = [];
  for await (const message of readSse(stream)) messages.push(message);
  return messages;
}

describe("readSse", () => {
  it("reads events with a name and data", async () => {
    const out = await collect(bodyOf('event: stage\ndata: {"stage":"prepare"}\n\n'));
    expect(out).toEqual([{ event: "stage", data: '{"stage":"prepare"}' }]);
  });

  it("reads several events in order", async () => {
    const out = await collect(bodyOf("event: a\ndata: 1\n\nevent: b\ndata: 2\n\n"));
    expect(out.map((m) => m.event)).toEqual(["a", "b"]);
  });

  it("puts an event back together when the network splits it", async () => {
    const out = await collect(
      bodyOf("eve", "nt: sta", "ge\nda", "ta: 1\n", "\nevent: b\ndata: 2\n\n"),
    );
    expect(out).toEqual([
      { event: "stage", data: "1" },
      { event: "b", data: "2" },
    ]);
  });

  it("handles a multi-byte character split between chunks", async () => {
    const bytes = new TextEncoder().encode("event: x\ndata: O(n²)\n\n");
    const cut = bytes.indexOf(0xc2) + 1; // between the two bytes of "²"
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(bytes.slice(0, cut));
        controller.enqueue(bytes.slice(cut));
        controller.close();
      },
    });
    expect(await collect(stream)).toEqual([{ event: "x", data: "O(n²)" }]);
  });

  it("accepts CRLF line endings, even split across chunks", async () => {
    const out = await collect(bodyOf("event: a\r\ndata: 1\r", "\n\r\nevent: b\r\ndata: 2\r\n\r\n"));
    expect(out).toEqual([
      { event: "a", data: "1" },
      { event: "b", data: "2" },
    ]);
  });

  it("ignores keep-alive comments", async () => {
    const out = await collect(bodyOf(": keep-alive\n\nevent: a\ndata: 1\n\n: keep-alive\n\n"));
    expect(out).toEqual([{ event: "a", data: "1" }]);
  });

  it("joins multi-line data with newlines", async () => {
    const out = await collect(bodyOf("event: a\ndata: line one\ndata: line two\n\n"));
    expect(out[0]?.data).toBe("line one\nline two");
  });

  it("defaults the event name to 'message'", async () => {
    expect(await collect(bodyOf("data: hello\n\n"))).toEqual([{ event: "message", data: "hello" }]);
  });

  it("keeps spaces after the first one in data", async () => {
    expect(await collect(bodyOf("data:  two spaces\n\n"))).toEqual([
      { event: "message", data: " two spaces" },
    ]);
  });

  it("drops an event that was cut off before its blank line", async () => {
    expect(await collect(bodyOf("event: a\ndata: 1\n\nevent: b\ndata: 2"))).toEqual([
      { event: "a", data: "1" },
    ]);
  });

  it("closes the connection when the reader stops early", async () => {
    let cancelled = false;
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        controller.enqueue(new TextEncoder().encode("event: a\ndata: 1\n\n"));
      },
      cancel() {
        cancelled = true;
      },
    });
    const messages = readSse(stream);
    await messages.next(); // read one event, then stop
    await messages.return(undefined);
    expect(cancelled).toBe(true);
  });
});
