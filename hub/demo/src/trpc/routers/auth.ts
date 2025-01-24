import { env } from '~/env';
import { authorizationModel } from '~/lib/models';

import { createTRPCRouter, publicProcedure } from '../trpc';

/*
  In production for app.near.ai and chat.near.ai, the value for AUTH_COOKIE_DOMAIN 
  will be "near.ai" - which will make the cookie accessible for near.ai and *.near.ai domains: 
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#define_where_cookies_are_sent
*/

export const AUTH_COOKIE_NAME = 'auth';
const AUTH_COOKIE_MAX_AGE_SECONDS = 31536000 * 100; // 100 years
const AUTH_COOKIE_STANDARD_FLAGS = `SameSite=Strict; Path=/; HttpOnly; Secure`;
const AUTH_COOKIE_FLAGS = env.AUTH_COOKIE_DOMAIN
  ? `${AUTH_COOKIE_STANDARD_FLAGS}; Domain=${env.AUTH_COOKIE_DOMAIN}`
  : AUTH_COOKIE_STANDARD_FLAGS;
export const AUTH_COOKIE_DELETE = `${AUTH_COOKIE_NAME}=null; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age: 0; ${AUTH_COOKIE_FLAGS}`;

export const authRouter = createTRPCRouter({
  saveToken: publicProcedure
    .input(authorizationModel)
    .mutation(({ ctx, input }) => {
      const authCookie = `${AUTH_COOKIE_NAME}=${encodeURIComponent(JSON.stringify(input))}; Max-Age=${AUTH_COOKIE_MAX_AGE_SECONDS}; ${AUTH_COOKIE_FLAGS}`;

      ctx.resHeaders.set('Set-Cookie', authCookie);

      return true;
    }),

  getToken: publicProcedure.query(({ ctx }) => {
    return ctx.signature;
  }),

  clearToken: publicProcedure.mutation(({ ctx }) => {
    ctx.resHeaders.set('Set-Cookie', AUTH_COOKIE_DELETE);
    return true;
  }),
});