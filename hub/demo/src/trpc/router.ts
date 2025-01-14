import { type inferRouterInputs, type inferRouterOutputs } from '@trpc/server';

import { authRouter } from './routers/auth';
import { hubRouter } from './routers/hub';
import { createCallerFactory, createTRPCRouter } from './trpc';

export const appRouter = createTRPCRouter({
  auth: authRouter,
  hub: hubRouter,
});

export type AppRouter = typeof appRouter;
export type AppRouterInputs = inferRouterInputs<AppRouter>;
export type AppRouterOutputs = inferRouterOutputs<AppRouter>;

export const createCaller = createCallerFactory(appRouter);
