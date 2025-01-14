import { TRPCClientError } from '@trpc/client';

import { type AppRouter } from '~/trpc/router';

export function isTRPCClientError(
  error: unknown,
): error is TRPCClientError<AppRouter> {
  return error instanceof TRPCClientError;
}
