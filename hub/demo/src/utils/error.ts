import { TRPCClientError } from '@trpc/client';

import { type appRouter } from '~/server/api/root';

export function isTRPCClientError(
  error: unknown,
): error is TRPCClientError<typeof appRouter> {
  return error instanceof TRPCClientError;
}
