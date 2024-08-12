"use client";

import { useMutation } from "@tanstack/react-query";
import { type z } from "zod";
import { env } from "~/env";
import { createAuthNearLink } from "~/lib/auth";
import { type chatCompletionsModel } from "~/lib/models";
import { api } from "~/trpc/react";

export const CONVERSATION_PATH = "current_conversation";
export const CALLBACK_URL = env.NEXT_PUBLIC_BASE_URL;
export const RECIPIENT = "ai.near";

export const MESSAGE = "Welcome to NEAR AI Hub!";
export const REVOKE_MESSAGE = "Are you sure? Revoking a nonce";
export const REVOKE_ALL_MESSAGE = "Are you sure? Revoking all nonces";

export function useSendCompletionsRequest() {
  const chatMut = api.hub.chat.useMutation();

  return useMutation({
    mutationFn: async (values: z.infer<typeof chatCompletionsModel>) => {
      console.log("Storing in localStorage the conversation", values);
      localStorage.setItem(CONVERSATION_PATH, JSON.stringify(values));

      const resp = await chatMut.mutateAsync(values);

      values.messages = [...values.messages, resp.choices[0]!.message];

      localStorage.setItem(CONVERSATION_PATH, JSON.stringify(values));

      return values;
    },
  });
}

export function useRevokeNonce() {
  return useMutation({
    mutationFn: async () => {
      const url = createAuthNearLink(MESSAGE, RECIPIENT, "11", CALLBACK_URL);
      window.location.replace(url);
    },
  });
}
