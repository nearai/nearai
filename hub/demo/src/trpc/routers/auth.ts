import { env } from '~/env';
import { authorizationModel } from '~/lib/models';

import { createTRPCRouter, publicProcedure } from '../trpc';

export const AUTH_COOKIE_NAME = 'auth';
const AUTH_COOKIE_MAX_AGE_SECONDS = 31536000 * 100; // 100 years
export const AUTH_COOKIE_DELETE = `${AUTH_COOKIE_NAME}=null; Max-Age=-1`;

export const authRouter = createTRPCRouter({
  saveToken: publicProcedure
    .input(authorizationModel)
    .mutation(({ ctx, input }) => {
      let authCookie = `${AUTH_COOKIE_NAME}=${encodeURIComponent(JSON.stringify(input))}; Max-Age=${AUTH_COOKIE_MAX_AGE_SECONDS}; HttpOnly; Secure`;

      if (env.AUTH_COOKIE_DOMAIN) {
        /*
          In production for app.near.ai and chat.near.ai, the value for AUTH_COOKIE_DOMAIN 
          will be "near.ai" - which will make the cookie accessible for near.ai and *.near.ai domains: 
          https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#define_where_cookies_are_sent
        */
        authCookie += `; Domain=${env.AUTH_COOKIE_DOMAIN}`;
      }

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
