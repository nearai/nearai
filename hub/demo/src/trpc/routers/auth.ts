import { authorizationModel } from '~/lib/models';

import { createTRPCRouter, publicProcedure } from '../trpc';

export const authRouter = createTRPCRouter({
  saveToken: publicProcedure
    .input(authorizationModel)
    .mutation(({ ctx, input }) => {
      console.log('Input:', input);
      console.log('Cookie:', ctx.req.headers.get('Cookie'));
      ctx.resHeaders.set('Set-Cookie', 'test=abc123');
      return true;
    }),
});
