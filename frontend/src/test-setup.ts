import "@testing-library/jest-dom/vitest";

// jsdom has no layout engine. CodeMirror measures text with these Range methods, so stub them.
const noRects = { length: 0, item: () => null, [Symbol.iterator]: function* () {} };
Range.prototype.getClientRects = () => noRects as unknown as DOMRectList;
Range.prototype.getBoundingClientRect = () => new DOMRect();
