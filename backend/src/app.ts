import helmet from "@fastify/helmet";
import Fastify, { type FastifyInstance } from "fastify";
import type { Config } from "./config.js";
import { healthRoutes } from "./routes/health.js";

/** Builds the app without starting it, so tests can call it with `app.inject()`. */
export async function buildApp(config: Config): Promise<FastifyInstance> {
  const app = Fastify({
    logger:
      config.NODE_ENV === "test"
        ? false
        : {
            level: config.LOG_LEVEL,
            ...(config.NODE_ENV === "development" && { transport: { target: "pino-pretty" } }),
          },
  });

  await app.register(helmet);
  await app.register(healthRoutes, { prefix: "/api" });

  return app;
}
