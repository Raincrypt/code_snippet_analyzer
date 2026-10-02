import { describe, expect, it } from "vitest";
import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";

describe("GET /api/health", () => {
  it("reports ok", async () => {
    const app = await buildApp(loadConfig({ NODE_ENV: "test" }));
    const response = await app.inject({ method: "GET", url: "/api/health" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({ status: "ok" });
    await app.close();
  });
});

describe("loadConfig", () => {
  it("applies defaults", () => {
    expect(loadConfig({})).toMatchObject({ PORT: 3001, NODE_ENV: "development" });
  });
  it("rejects an invalid port", () => {
    expect(() => loadConfig({ PORT: "not-a-number" })).toThrow(/Invalid environment/);
  });
});
