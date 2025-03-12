import { createEnv } from '@t3-oss/env-nextjs';
import { z } from 'zod';

export const env = createEnv({
  /**
   * Specify your server-side environment variables schema here. This way you can ensure the app
   * isn't built with invalid env vars.
   */
  server: {
    HOME: z.string().optional(),
    NODE_ENV: z.enum(['development', 'test', 'production']),
    ROUTER_URL: z.string().url(),
    DATA_SOURCE: z.enum(['registry', 'local_files']).default('registry'),
    AUTH_COOKIE_DOMAIN: z.string().optional(),
    NEAR_RPC_URL: z.string().url().default('https://rpc.mainnet.near.org'),
  },

  /**
   * Specify your client-side environment variables schema here. This way you can ensure the app
   * isn't built with invalid env vars. To expose them to the client, prefix them with
   * `NEXT_PUBLIC_`.
   */
  client: {
    NEXT_PUBLIC_BASE_URL: z.string().url(),
    NEXT_PUBLIC_CONSUMER_MODE: z.preprocess(
      (val) => (val === 'true' ? true : false),
      z.boolean(),
    ),
    NEXT_PUBLIC_CHAT_AGENT_ID: z
      .string()
      .regex(/.+\/.+\/.+/)
      .default('zavodil.near/pm-agent/1'),
    NEXT_PUBLIC_EXAMPLE_FORK_AGENT_ID: z
      .string()
      .regex(/.+\/.+\/.+/)
      .default('zavodil.near/pm-agent/1'),
    NEXT_PUBLIC_AUTH_URL: z.string().url().optional(),
    NEXT_PUBLIC_FEATURED_AGENT_IDS: z.preprocess((val) => {
      if (typeof val === 'string' && val) {
        const ids = (val ?? '')
          .split(',')
          .map((id) => id.trim())
          .filter((id) => Boolean(id));
        return ids;
      }

      return [
        'jayzalowitz.near/memecoin_agent/latest',
        'zavodil.near/pm-agent/latest',
        'flatirons.near/xela-agent/latest',
      ];
    }, z.string().array()),
  },

  /**
   * You can't destruct `process.env` as a regular object in the Next.js edge runtimes (e.g.
   * middlewares) or client-side so we need to destruct manually.
   */
  runtimeEnv: {
    NODE_ENV: process.env.NODE_ENV,
    NEAR_RPC_URL: process.env.NEAR_RPC_URL,
    ROUTER_URL: process.env.ROUTER_URL,
    NEXT_PUBLIC_BASE_URL: process.env.NEXT_PUBLIC_VERCEL_URL
      ? `https://${process.env.NEXT_PUBLIC_VERCEL_URL}`
      : process.env.NEXT_PUBLIC_BASE_URL,
    DATA_SOURCE: process.env.DATA_SOURCE,
    HOME: process.env.HOME,
    NEXT_PUBLIC_CONSUMER_MODE: process.env.NEXT_PUBLIC_CONSUMER_MODE,
    NEXT_PUBLIC_CHAT_AGENT_ID:
      process.env.NEXT_PUBLIC_CHAT_AGENT_ID ||
      process.env.NEXT_PUBLIC_CONSUMER_CHAT_AGENT_ID,
    NEXT_PUBLIC_AUTH_URL:
      process.env.NEXT_PUBLIC_AUTH_URL ?? 'https://auth.near.ai',
    NEXT_PUBLIC_EXAMPLE_FORK_AGENT_ID:
      process.env.NEXT_PUBLIC_EXAMPLE_FORK_AGENT_ID,
    NEXT_PUBLIC_FEATURED_AGENT_IDS: process.env.NEXT_PUBLIC_FEATURED_AGENT_IDS,
    AUTH_COOKIE_DOMAIN: process.env.AUTH_COOKIE_DOMAIN,
  },
  /**
   * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially
   * useful for Docker builds.
   */
  skipValidation: !!process.env.SKIP_ENV_VALIDATION,
  /**
   * Makes it so that empty strings are treated as undefined. `SOME_VAR: z.string()` and
   * `SOME_VAR=''` will throw an error.
   */
  emptyStringAsUndefined: true,
});
