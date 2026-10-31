export type SseMessage = { event: string; data: string };

/** Turns one block of lines (an event without its blank-line terminator) into a message. */
function parseBlock(block: string): SseMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line === "" || line.startsWith(":")) continue; // blank lines and comments (keep-alives)
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    // One optional space after the colon belongs to the format, not to the value.
    const value = colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "");
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  return data.length === 0 ? null : { event, data: data.join("\n") };
}

/**
 * Reads a Server-Sent Events response body. Handles events split across network chunks,
 * CRLF line endings, comments and multi-line data. Stops reading (and closes the connection)
 * when the consumer stops iterating.
 */
export async function* readSse(stream: ReadableStream<Uint8Array>): AsyncGenerator<SseMessage> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // A lone trailing \r may be half of a \r\n split across chunks, so leave it for later.
      const held = buffer.endsWith("\r") ? "\r" : "";
      buffer = buffer.slice(0, buffer.length - held.length).replace(/\r\n|\r/g, "\n") + held;
      for (let end = buffer.indexOf("\n\n"); end !== -1; end = buffer.indexOf("\n\n")) {
        const message = parseBlock(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        if (message) yield message;
      }
    }
    // Whatever is left was never terminated by a blank line, so it is an incomplete event.
  } finally {
    await reader.cancel().catch(() => {});
  }
}
