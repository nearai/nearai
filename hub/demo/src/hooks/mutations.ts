"use client";

import { useMutation } from "@tanstack/react-query";
import { type z } from "zod";
import { env } from "~/env";
import { type chatCompletionsModel } from "~/lib/models";
import { api } from "~/trpc/react";

export const CONVERSATION_PATH = "current_conversation";
export const CALLBACK_URL = env.NEXT_PUBLIC_BASE_URL;
export const PLAIN_MSG = "test message to sign";
export const CURRENT_AUTH = "current_auth";
export const RECIPIENT = "ai.near";
export const NONCE = "12345678901234567890123456789012"

export function useSendCompletionsRequest() {
  const chatMut = api.router.chat.useMutation();

  return useMutation({
    mutationFn: async (values: z.infer<typeof chatCompletionsModel>) => {
      console.log("Storing in localStorage the conversation");
      localStorage.setItem(CONVERSATION_PATH, JSON.stringify(values));

      const currAuth = localStorage.getItem(CURRENT_AUTH);

      return await chatMut.mutateAsync(values);
    },
  });
}
