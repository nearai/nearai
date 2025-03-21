import { initTRPC, TRPCError } from '@trpc/server';
import { type FetchCreateContextFnOptions } from '@trpc/server/adapters/fetch';
import superjson from 'superjson';
import { ZodError } from 'zod';

import { parseAuthCookie } from '@/utils/cookies';

import { AUTH_COOKIE_DELETE } from './routers/auth';

export const createTRPCContext = async (opts: FetchCreateContextFnOptions) => {
  const { error, authorization, signature } = parseAuthCookie(opts.req);

  if (error) {
    opts.resHeaders.set('Set-Cookie', AUTH_COOKIE_DELETE);
  }

  return {
    ...opts,
    authorization,
    signature,
  };
};

const t = initTRPC.context<typeof createTRPCContext>().create({
  transformer: superjson,
  errorFormatter({ shape, error }) {
    return {
      ...shape,
      data: {
        ...shape.data,
        zodError:
          error.cause instanceof ZodError ? error.cause.flatten() : null,
      },
    };
  },
});

export const createTRPCRouter = t.router;
export const createCallerFactory = t.createCallerFactory;

// Public procedures for when a user may or may not be signed in:

export const publicProcedure = t.procedure;

// Protected procedures where a user is required to be signed in:

export const protectedProcedure = t.procedure.use(
  t.middleware(({ ctx, next }) => {
    if (!ctx.authorization || !ctx.signature) {
      throw new TRPCError({ code: 'UNAUTHORIZED' });
    }

    return next({
      ctx: {
        ...ctx,
        authorization: ctx.authorization,
        signature: ctx.signature,
      },
    });
  }),
);
