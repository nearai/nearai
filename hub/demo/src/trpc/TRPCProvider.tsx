'use client';

import type { QueryClient } from '@tanstack/react-query';
import { QueryClientProvider } from '@tanstack/react-query';
import { httpBatchLink, loggerLink, type TRPCLink } from '@trpc/client';
import { createTRPCQueryUtils, createTRPCReact } from '@trpc/react-query';
import { observable } from '@trpc/server/observable';
import { useState } from 'react';
import superjson from 'superjson';

import { useAuthStore } from '@/stores/auth';

import { makeQueryClient } from './query-client';
import type { AppRouter } from './router';

export const trpc = createTRPCReact<AppRouter>();

let clientQueryClientSingleton: QueryClient;

function getQueryClient() {
  if (typeof window === 'undefined') return makeQueryClient();
  return (clientQueryClientSingleton ??= makeQueryClient());
}

function getUrl() {
  const base = (() => {
    if (typeof window !== 'undefined') return '';
    if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
    return 'http://localhost:3000';
  })();
  return `${base}/api/trpc`;
}

const globalErrorHandlingLink: TRPCLink<AppRouter> = () => {
  return ({ next, op }) => {
    return observable((observer) => {
      const unsubscribe = next(op).subscribe({
        next(value) {
          observer.next(value);
        },
        error(error) {
          observer.error(error);

          if (
            error?.data?.code === 'UNAUTHORIZED' &&
            typeof window !== 'undefined'
          ) {
            useAuthStore.setState({
              unauthorizedErrorHasTriggered: true,
            });
          }
        },
        complete() {
          observer.complete();
        },
      });

      return unsubscribe;
    });
  };
};

const links = [
  globalErrorHandlingLink,

  loggerLink({
    enabled: (opts) =>
      (process.env.NODE_ENV === 'development' &&
        typeof window !== 'undefined') ||
      (opts.direction === 'down' && opts.result instanceof Error),
  }),

  httpBatchLink({
    transformer: superjson,
    url: getUrl(),
  }),
];

export const clientUtils = createTRPCQueryUtils({
  queryClient: getQueryClient(),
  client: trpc.createClient({
    links,
  }),
});

export function TRPCProvider(
  props: Readonly<{
    children: React.ReactNode;
  }>,
) {
  const queryClient = getQueryClient();

  const [trpcClient] = useState(() =>
    trpc.createClient({
      links,
    }),
  );

  return (
    <trpc.Provider client={trpcClient} queryClient={queryClient}>
      <QueryClientProvider client={queryClient}>
        {props.children}
      </QueryClientProvider>
    </trpc.Provider>
  );
}
