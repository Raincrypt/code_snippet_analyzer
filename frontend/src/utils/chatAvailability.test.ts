import { chatBlockedReason } from "./chatAvailability";

const CODE = "const a = 1;";

describe("chatBlockedReason", () => {
  it("blocks chat before any review", () => {
    expect(chatBlockedReason("idle", null, CODE)).toMatch(/review your code/i);
  });

  it("blocks chat while a review is running", () => {
    expect(chatBlockedReason("loading", null, CODE)).toMatch(/reviewing/i);
  });

  it("blocks chat after a failed review", () => {
    expect(chatBlockedReason("error", null, CODE)).toMatch(/didn’t finish/i);
  });

  it("allows chat when the code matches what was reviewed", () => {
    expect(chatBlockedReason("success", CODE, CODE)).toBeNull();
  });

  it("blocks chat once the code is edited", () => {
    expect(chatBlockedReason("success", CODE, CODE + "x")).toMatch(/code changed/i);
  });

  it("allows chat again when the edit is reverted", () => {
    expect(chatBlockedReason("success", CODE, CODE + "x")).not.toBeNull();
    expect(chatBlockedReason("success", CODE, CODE)).toBeNull();
  });

  it("treats whitespace-only edits as edits", () => {
    expect(chatBlockedReason("success", CODE, CODE + " ")).not.toBeNull();
  });
});
