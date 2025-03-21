import { createTRPCRouter, publicProcedure } from '../trpc';

export const AUTH_COOKIE_NAME = 'auth';

export const authRouter = createTRPCRouter({
  getSession: publicProcedure.query(({ ctx }) => {
    if (!ctx.signature) return null;

    return {
      accountId: ctx.signature.account_id,
    };
  }),

  signOut: publicProcedure.mutation(() => {
    // TODO: Call auth sign out endpoint to clear cookie?
    return true;
  }),
});
