import { TRPCError } from '@trpc/server';
import { z } from 'zod';

import { env } from '~/env';

import { createTRPCRouter, publicProcedure } from '../trpc';

export const protocolRouter = createTRPCRouter({
  loadJson: publicProcedure
    .input(
      z.object({
        url: z.string().url(),
      }),
    )
    .query(async ({ input }) => {
      let { url } = input;

      try {
        if (env.NODE_ENV === 'development') {
          const passedUrl = url;
          url = url.replace('https://app.near.ai', env.NEXT_PUBLIC_BASE_URL);
          console.warn(
            `Due to NODE_ENV=development, loadJson url parameter was modified to point to NEXT_PUBLIC_BASE_URL`,
            {
              passedUrl,
              requestedUrl: url,
            },
          );
        }

        const response = await fetch(url);
        const data: unknown = await response
          .json()
          .catch(() => response.text());

        if (!response.ok) throw data;

        return data;
      } catch (error) {
        console.error(`Failed to load JSON at URL: ${url}`, error);

        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: `Failed to load JSON at URL: ${url}`,
        });
      }
    }),
});
