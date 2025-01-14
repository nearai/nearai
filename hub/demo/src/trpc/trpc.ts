import { initTRPC, TRPCError } from '@trpc/server';
import { type FetchCreateContextFnOptions } from '@trpc/server/adapters/fetch';
import superjson from 'superjson';
import { type z, ZodError } from 'zod';

import { authorizationModel } from '~/lib/models';

export const createTRPCContext = async (opts: FetchCreateContextFnOptions) => {
  return {
    ...opts,
    authorization: opts.req.headers.get('Authorization'), // TODO: This should pull from a cookie
  };
};

// export const createTRPCContext = cache(async () => {
//   /**
//    * @see: https://trpc.io/docs/server/context
//    */
//   return { userId: 'user_123' };
// });

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

const userMightBeAuthenticated = t.middleware(({ ctx, next }) => {
  const authorization = ctx.authorization;
  let signature: z.infer<typeof authorizationModel> | undefined;

  if (authorization?.includes('Bearer')) {
    try {
      const auth: unknown = JSON.parse(authorization.replace('Bearer ', ''));
      signature = authorizationModel.parse(auth);
    } catch (error) {
      console.error(error);
    }
  }

  return next({
    ctx: {
      ...ctx,
      authorization,
      signature,
    },
  });
});

export const publicProcedure = t.procedure.use(userMightBeAuthenticated);

// Protected procedures where a user is required to be signed in:

const enforceUserIsAuthenticated = t.middleware(({ ctx, next }) => {
  if (!ctx.authorization?.includes('Bearer')) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }

  const auth: unknown = JSON.parse(ctx.authorization.replace('Bearer ', ''));
  const sig = authorizationModel.parse(auth);

  return next({
    ctx: {
      ...ctx,
      authorization: ctx.authorization,
      signature: sig,
    },
  });
});

export const protectedProcedure = t.procedure.use(enforceUserIsAuthenticated);
