import { z } from "zod";

export const authorizationModel = z.object({
  account_id: z.string(),
  public_key: z.string(),
  signature: z.string(),
  callback_url: z.string(),
  message: z.string(),
  recipient: z.string(),
  nonce: z.string().regex(/^\d{32}$/), // String containing exactly 32 digits
});

export const messageModel = z.object({
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
});

export const chatCompletionsModel = z.object({
  max_tokens: z.number().default(64),
  temperature: z.number().default(0.1),
  frequency_penalty: z.number().default(0),
  n: z.number().default(1),
  messages: z.array(messageModel),
  model: z.string(),
  provider: z.string(),
  // TODO: add more fields here
});

export const chatResponseModel = z.object({
  id: z.string(),
  choices: z.array(
    z.object({
      finish_reason: z.string(),
      index: z.number(),
      logprobs: z.unknown().nullable(),
      message: messageModel,
    }),
  ),
  created: z.number(),
  model: z.string(),
  object: z.string(),
  system_fingerprint: z.unknown().nullable(),
  usage: z.object({
    completion_tokens: z.number(),
    prompt_tokens: z.number(),
    total_tokens: z.number(),
  }),
});

export const listModelsModel = z.object({
  provider: z.string(),
});

export const oneModelModel = z.object({
  id: z.string(),
  created: z.number(),
  object: z.string(),
  owned_by: z.string(),
  number_of_inference_nodes: z.number().nullable().optional(),
  supports_chat: z.boolean(),
  supports_image_input: z.boolean(),
  supports_tools: z.boolean(),
  context_length: z.number().nullable().optional(),
});

export const listModelsResponseModel = z.object({
  data: z.array(oneModelModel),
  object: z.string(),
});

export const challengeResponseModel = z.object({
  challenge: z.string(),
});

export const nonceModel = z.object({
  nonce: z.string(),
  account_id: z.string(),
  message: z.string(),
  recipient: z.string(),
  callback_url: z.string(),
  nonce_status: z.enum(["active", "revoked"]),
  first_seen_at: z.string(),
});

export const listNoncesModel = z.array(nonceModel);

export const revokeNonceModel = z.object({
  nonce: z.string().regex(/^\d{32}$/),
  auth: z.string(),
});

export const registryEntry = z.object({
  namespace: z.string(),
  name: z.string(),
  version: z.string(),
});
export const listRegistry = z.array(registryEntry);
