import { env } from "~/env";
import {
  chatCompletionsModel,
  chatResponseModel,
  listModelsResponseModel,
  listNoncesModel,
  listRegistry,
  revokeNonceModel,
} from "~/lib/models";
import { createZodFetcher } from "zod-fetch";

import {
  createTRPCRouter,
  protectedProcedure,
  publicProcedure,
} from "~/server/api/trpc";
import { z } from "zod";

const fetchWithZod = createZodFetcher();

export const hubRouter = createTRPCRouter({
  listModels: publicProcedure.query(async () => {
    const u = env.ROUTER_URL + "/models";

    const response = await fetch(u);
    const resp: unknown = await response.json();

    return listModelsResponseModel.parse(resp);
  }),

  chat: protectedProcedure
    .input(chatCompletionsModel)
    .mutation(async ({ ctx, input }) => {
      const u = env.ROUTER_URL + "/chat/completions";

      const response = await fetch(u, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: ctx.Authorization!,
        },
        body: JSON.stringify(input),
      });

      // check for errors
      if (!response.ok) {
        throw new Error(
          "Failed to send chat completions, status: " +
            response.status +
            " " +
            response.statusText,
        );
      }

      const resp: unknown = await response.json();

      return chatResponseModel.parse(resp);
    }),

  listNonces: protectedProcedure.query(async ({ ctx }) => {
    const u = env.ROUTER_URL + "/nonce/list";

    const resp = await fetchWithZod(listNoncesModel, u, {
      headers: {
        Authorization: ctx.Authorization!,
      },
    });
    console.log(resp);

    return resp;
  }),

  revokeNonce: protectedProcedure
    .input(revokeNonceModel)
    .mutation(async ({ input }) => {
      const u = env.ROUTER_URL + "/nonce/revoke";

      try {
        // We can't use regular auth since we need to use the signed revoke message.
        const resp = await fetch(u, {
          headers: {
            Authorization: input.auth,
            "Content-Type": "application/json",
          },
          method: "POST",
          body: JSON.stringify({ nonce: input.nonce }),
        });
        return resp;
      } catch (e) {
        console.log(e);
        throw e;
      }
    }),

  revokeAllNonces: protectedProcedure
    .input(z.object({ auth: z.string() }))
    .mutation(async ({ input }) => {
      const u = env.ROUTER_URL + "/nonce/revoke/all";

      try {
        // We can't use regular auth since we need to use the signed revoke message.
        const resp = await fetch(u, {
          headers: {
            Authorization: input.auth,
            "Content-Type": "application/json",
          },
          method: "POST",
        });
        return resp;
      } catch (e) {
        console.log(e);
        throw e;
      }
    }),

  listRegistry: publicProcedure
    .input(z.object({ category: z.string() }))
    .query(async ({ input }) => {
      const u =
        env.ROUTER_URL + "/registry/list_entries?category=" + input.category;

      const resp = await fetchWithZod(listRegistry, u, {
        method: "POST",
      });
      console.log(resp);

      return resp;
    }),
});
