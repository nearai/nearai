import { TRPCClientError } from '@trpc/client';
import { type TRPCError } from '@trpc/server';

import { type AppRouter } from '@/trpc/router';

export function isTRPCClientError(
  error: unknown,
): error is TRPCClientError<AppRouter> {
  return error instanceof TRPCClientError;
}

export function statusCodeToTRPCErrorCode(
  statusCode: string | number,
): TRPCError['code'] {
  const code = statusCode.toString();

  if (code === '400') return 'BAD_REQUEST';
  if (code === '401') return 'UNAUTHORIZED';
  if (code === '403') return 'FORBIDDEN';
  if (code === '404') return 'NOT_FOUND';

  return 'INTERNAL_SERVER_ERROR';
}
