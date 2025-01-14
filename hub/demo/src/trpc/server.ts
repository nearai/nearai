import 'server-only';

import { createHydrationHelpers } from '@trpc/react-query/rsc';
import { cache } from 'react';

import { makeQueryClient } from './query-client';
import { appRouter } from './router';
import { createCallerFactory, createTRPCContext } from './trpc';

export const getQueryClient = cache(makeQueryClient);

// @ts-expect-error https://trpc.io/docs/client/react/server-components#5-create-a-trpc-caller-for-server-components
const caller = createCallerFactory(appRouter)(createTRPCContext);

export const { trpc, HydrateClient } = createHydrationHelpers<typeof appRouter>(
  caller,
  getQueryClient,
);
