/* eslint-disable @typescript-eslint/no-explicit-any */

import { TRPCError } from '@trpc/server';
import { type z } from 'zod';

import { statusCodeToTRPCErrorCode } from './error';

type AnyFetcher = (...args: any[]) => any;

type Schema<TData> =
  | {
      passthrough: () => {
        safeParse: (data: unknown) => z.SafeParseReturnType<unknown, TData>;
      };
    }
  | { safeParse: (data: unknown) => z.SafeParseReturnType<unknown, TData> };

type ZodFetcher<TFetcher extends AnyFetcher> = <TData>(
  schema: Schema<TData>,
  ...args: Parameters<TFetcher>
) => Promise<TData>;

const defaultFetcher = async (...args: Parameters<typeof fetch>) => {
  const response = await fetch(...args);

  if (!response.ok) {
    try {
      const body = await response.json().catch(() => response.text());
      console.error(body);
    } catch (_error) {}

    throw new TRPCError({
      code: statusCodeToTRPCErrorCode(response.status),
      message: `Request failed with status: ${response.status}`,
    });
  }

  return response.json();
};

/**
 * Creates a `fetchWithZod` function that takes in a schema of
 * the expected response, and the arguments to fetch.
 *
 * Since you didn't provide a fetcher in `createZodFetcher()`,
 * we're falling back to the default fetcher.
 *
 * @example
 *
 * const fetchWithZod = createZodFetcher();
 *
 * const response = await fetchWithZod(
 *   z.object({
 *     hello: z.string(),
 *   }),
 *   "https://example.com",
 * );
 */
export function createZodFetcher(): ZodFetcher<typeof fetch>;

/**
 * Creates a `fetchWithZod` function that takes in a schema of
 * the expected response, and the arguments to the fetcher
 * you provided.
 *
 * @example
 *
 * const fetchWithZod = createZodFetcher((url) => {
 *   return fetch(url).then((res) => res.json());
 * });
 *
 * const response = await fetchWithZod(
 *   z.object({
 *     hello: z.string(),
 *   }),
 *   "https://example.com",
 * );
 */
export function createZodFetcher<TFetcher extends AnyFetcher>(
  /**
   * A fetcher function that returns the data you'd like to parse
   * with the schema.
   */
  fetcher: TFetcher,
): ZodFetcher<TFetcher>;
export function createZodFetcher(
  fetcher: AnyFetcher = defaultFetcher,
): ZodFetcher<any> {
  return async (schema, ...args) => {
    const response = await fetcher(...args);

    let parsed;
    if ('passthrough' in schema) {
      parsed = schema.passthrough().safeParse(response);
    } else {
      parsed = schema.safeParse(response);
    }

    if (parsed.error) {
      console.error(
        'API response failed to match expected Zod schema',
        parsed.error,
      );

      throw new TRPCError({
        code: 'INTERNAL_SERVER_ERROR',
        message: parsed.error.message,
      });
    }

    return parsed.data;
  };
}
