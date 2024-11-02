/**
 * YOU PROBABLY DON'T NEED TO EDIT THIS FILE, UNLESS:
 * 1. You want to modify request context (see Part 1).
 * 2. You want to create a new middleware or type of procedure (see Part 3).
 *
 * TL;DR - This is where all the tRPC server stuff is created and plugged in. The pieces you will
 * need to use are documented accordingly near the end.
 */
import { initTRPC, TRPCError } from '@trpc/server';
import { headers } from 'next/headers';
import superjson from 'superjson';
import { type z, ZodError } from 'zod';

import { authorizationModel } from '~/lib/models';

/**
 * 1. CONTEXT
 *
 * This section defines the "contexts" that are available in the backend API.
 *
 * These allow you to access things when processing a request, like the database, the session, etc.
 *
 * This helper generates the "internals" for a tRPC context. The API handler and RSC clients each
 * wrap this and provides the required context.
 *
 * @see https://trpc.io/docs/server/context
 */
export const createTRPCContext = async (opts: { headers: Headers }) => {
  const h = headers().has('Authorization')
    ? { authorization: headers().get('Authorization') }
    : undefined;

  return {
    ...opts,
    ...h,
  };
};

/**
 * 2. INITIALIZATION
 *
 * This is where the tRPC API is initialized, connecting the context and transformer. We also parse
 * ZodErrors so that you get typesafety on the frontend if your procedure fails due to validation
 * errors on the backend.
 */
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

/**
 * Create a server-side caller.
 *
 * @see https://trpc.io/docs/server/server-side-calls
 */
export const createCallerFactory = t.createCallerFactory;

/**
 * 3. ROUTER & PROCEDURE (THE IMPORTANT BIT)
 *
 * These are the pieces you use to build your tRPC API. You should import these a lot in the
 * "/src/server/api/routers" directory.
 */

/**
 * This is how you create new routers and sub-routers in your tRPC API.
 *
 * @see https://trpc.io/docs/router
 */
export const createTRPCRouter = t.router;

/**
 * Public (unauthenticated) procedure
 *
 * This is the base piece you use to build new queries and mutations on your tRPC API. It does not
 * guarantee that a user querying is authorized, but you can still access user session data if they
 * are logged in.
 */
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
      authorization,
      signature,
    },
  });
});
export const publicProcedure = t.procedure.use(userMightBeAuthenticated);

/** Reusable middleware that enforces users are logged in before running the procedure. */
const enforceUserIsAuthenticated = t.middleware(({ ctx, next }) => {
  if (!ctx.authorization?.includes('Bearer')) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }

  const auth: unknown = JSON.parse(ctx.authorization.replace('Bearer ', ''));
  const sig = authorizationModel.parse(auth);

  return next({
    ctx: {
      authorization: ctx.authorization,
      signature: sig,
    },
  });
});

export const protectedProcedure = t.procedure.use(enforceUserIsAuthenticated);
