import { type z } from 'zod';

import { authorizationModel } from '@/lib/models';
import { AUTH_COOKIE_NAME } from '@/trpc/routers/auth';

export function parseCookies(str: string) {
  const result: Record<string, string> = {};

  return str
    .split(';')
    .map((v) => v.split('='))
    .reduce((result, v) => {
      const key = v[0]?.trim();
      const value = v[1]?.trim();

      if (key && value) {
        result[decodeURIComponent(key)] = decodeURIComponent(value);
      }

      return result;
    }, result);
}

export function parseAuthCookie(req: Request) {
  const cookies = parseCookies(req.headers.get('Cookie') ?? '');
  const rawAuth = cookies[AUTH_COOKIE_NAME];
  let authorization: string | null = null;
  let signature: z.infer<typeof authorizationModel> | null = null;
  let error: unknown = undefined;

  if (rawAuth) {
    try {
      signature = authorizationModel.parse(JSON.parse(rawAuth));
      authorization = `Bearer ${JSON.stringify(signature)}`;
    } catch (e) {
      console.error(e);
      error = e;
    }
  }

  return {
    authorization,
    error,
    signature,
  };
}
