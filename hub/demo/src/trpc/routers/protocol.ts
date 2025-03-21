import { TRPCError } from '@trpc/server';
import { z } from 'zod';

import { env } from '@/env';

import { createTRPCRouter, publicProcedure } from '../trpc';

export const protocolRouter = createTRPCRouter({
  loadJson: publicProcedure
    .input(
      z.object({
        url: z.string().url(),
      }),
    )
    .query(async ({ input }) => {
      const originalUrl = input.url;

      try {
        if (env.NODE_ENV === 'development') {
          input.url = input.url.replace(
            'https://app.near.ai',
            env.NEXT_PUBLIC_BASE_URL,
          );
          console.warn(
            `Due to NODE_ENV=development, loadJson url parameter was modified to point to NEXT_PUBLIC_BASE_URL`,
            {
              originalUrl,
              modifiedUrl: input.url,
            },
          );
        }

        const response = await fetch(input.url);
        const data: unknown = await response
          .json()
          .catch(() => response.text());

        if (!response.ok) throw data;

        return data;
      } catch (error) {
        console.error(`Failed to load JSON at URL: ${originalUrl}`, error);

        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: `Failed to load JSON at URL: ${originalUrl}`,
        });
      }
    }),
});
