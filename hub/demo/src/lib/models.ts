import { z } from 'zod';

import { parseStringOrNumber } from '~/utils/number';

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
  role: z.enum(['user', 'assistant', 'system']),
  content: z.string(),
});

export const chatWithAgentModel = z.object({
  agent_id: z.string(),
  new_message: z.string(),
  environment_id: z.string().nullable().optional(),
  max_iterations: z.number(),
  user_env_vars: z.record(z.string(), z.unknown()).nullable().optional(),
  agent_env_vars: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const chatWithModelModel = z.object({
  max_tokens: z.number().default(64),
  temperature: z.number().default(0.1),
  frequency_penalty: z.number().default(0),
  n: z.number().default(1),
  messages: z.array(messageModel),
  model: z.string(),
  provider: z.string(),
  stop: z.array(z.string()).default([]),
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

export const modelModel = z.object({
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

export const modelsModel = z.object({
  data: z.array(modelModel),
  object: z.string(),
});

export const challengeModel = z.object({
  challenge: z.string(),
});

export const nonceModel = z.object({
  nonce: z.string(),
  account_id: z.string(),
  message: z.string(),
  recipient: z.string(),
  callback_url: z.string(),
  nonce_status: z.enum(['active', 'revoked']),
  first_seen_at: z.string(),
});

export const noncesModel = z.array(nonceModel);

export const revokeNonceModel = z.object({
  nonce: z.string().regex(/^\d{32}$/),
  auth: z.string(),
});

export const entryCategory = z.enum([
  'agent',
  'benchmark',
  'dataset',
  'environment',
  'evaluation',
  'model',
]);
export type EntryCategory = z.infer<typeof entryCategory>;

export const entryDetailsModel = z.intersection(
  z
    .object({
      agent: z
        .object({
          welcome: z
            .object({
              title: z.string(),
              description: z.string(),
            })
            .partial(),
        })
        .partial(),
      env_vars: z.record(z.string(), z.string()),
      primary_agent_name: z.string(),
      primary_agent_namespace: z.string(),
      primary_agent_version: z.string(),
      base_id: z.string().or(z.null()),
      icon: z.string(),
      run_id: z.coerce.string(),

      timestamp: z.string(),
    })
    .partial(),
  z.record(z.string(), z.unknown()),
);

export const entryModel = z.object({
  id: z.number(),
  category: entryCategory,
  namespace: z.string(),
  name: z.string(),
  version: z.string(),
  description: z.string().default(''),
  tags: z.string().array().default([]),
  show_entry: z.boolean().default(true),
  starred_by_point_of_view: z.boolean().default(false),
  num_stars: z.number().default(0),
  details: entryDetailsModel.default({}),
});

export const entriesModel = z.array(entryModel);

export const fileModel = z.object({
  filename: z.string(),
});

export const filesModel = fileModel.array();

export const evaluationTableRowModel = z.intersection(
  z.object({
    agent: z.string(),
    agentId: z.string().optional(),
    model: z.string(),
    namespace: z.string(),
    provider: z.string(),
    version: z.string(),
  }),
  z.record(
    z.string(),
    z.preprocess(parseStringOrNumber, z.string().or(z.number())),
  ),
);

export const evaluationsTableModel = z.object({
  columns: z.string().array(),
  important_columns: z.string().array(),
  rows: evaluationTableRowModel.array(),
});

export const entrySecretModel = z.object({
  namespace: z.string(),
  name: z.string(),
  version: z.string().optional(),
  description: z.string().default(''),
  key: z.string(),
  value: z.string(),
  category: z.string().optional(),
});
