import { z } from 'zod';

export const apiErrorModel = z.object({
  detail: z.string(),
});

export const authorizationModel = z.object({
  account_id: z.string(),
  public_key: z.string(),
  signature: z.string(),
  callback_url: z.string(),
  message: z.string(),
  recipient: z.string(),
  nonce: z.string().regex(/^\d{32}$/), // String containing exactly 32 digits
});

export const chatWithAgentModel = z.object({
  agent_id: z.string(),
  attachments: z
    .object({
      file_id: z.string(),
      tools: z.unknown().array().nullish(),
    })
    .array()
    .nullish(),
  new_message: z.string(),
  thread_id: z.string().nullable().optional(),
  max_iterations: z.number().optional(),
  user_env_vars: z.record(z.string(), z.unknown()).nullable().optional(),
  agent_env_vars: z.record(z.string(), z.unknown()).nullable().optional(),
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

export const optionalVersion = z.preprocess(
  (value) => (!value || value === 'latest' || value === '*' ? '' : value),
  z.string(),
);

export const entryDetailsModel = z.intersection(
  z
    .object({
      agent: z
        .object({
          assistant_role_label: z.string(),
          defaults: z
            .object({
              max_iterations: z.number(),
            })
            .partial(),
          embed: z
            .object({
              logo: z.string().or(z.literal(false)),
            })
            .partial(),
          html_height: z.enum(['auto']).or(z.string()).default('auto'),
          html_show_latest_messages_below: z.boolean().default(false),
          initial_user_message: z.string(),
          allow_message_attachments: z.boolean().default(false),
          allow_message_attachments_accept_mime_types: z
            .string()
            .array()
            .optional(), // https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/accept
          show_streaming_message: z.boolean().default(true),
          welcome: z
            .object({
              title: z.string(),
              description: z.string(),
              icon: z.string(),
            })
            .partial(),
        })
        .partial()
        .default({}),
      env_vars: z.record(z.string(), z.string()),
      primary_agent_name: z.string(),
      primary_agent_namespace: z.string(),
      primary_agent_version: z.string(),
      private_source: z.boolean().default(false),
      base_id: z.string().or(z.null()),
      icon: z.string(),
      run_id: z.coerce.string(),
      timestamp: z.string(),
    })
    .partial()
    .default({}),
  z.record(z.string(), z.unknown()),
);

export const entryModel = z
  .object({
    id: z.number(),
    category: entryCategory,
    namespace: z.string(),
    name: z.string(),
    version: z.string(),
    updated: z.string().datetime().default(new Date().toISOString()),
    description: z.string().default(''),
    tags: z.string().array().default([]),
    show_entry: z.boolean().default(true),
    starred_by_point_of_view: z.boolean().default(false),
    num_forks: z.number().default(0),
    num_stars: z.number().default(0),
    details: entryDetailsModel.default({}),
    fork_of: z
      .object({
        name: z.string(),
        namespace: z.string(),
      })
      .nullish(),
  })
  .passthrough();

export const entriesModel = z.array(entryModel);

export const entryFilesModel = z
  .object({
    filename: z.string(),
  })
  .array();

export const evaluationTableRowModel = z.intersection(
  z.object({
    agent: z.string(),
    agentId: z.string().optional(),
    competition_row_tags: z
      .enum([
        'baseline',
        'reference',
        'submission',
        'successful_submission',
        'disqualified_submission',
      ])
      .array()
      .default([]),
    model: z.string(),
    modelId: z.string().optional(),
    namespace: z.string(),
    provider: z.string(),
    version: z.string(),
  }),
  z.record(z.string(), z.string().or(z.number())),
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
  description: z.string().nullable().default(''),
  key: z.string(),
  value: z.string(),
  category: z.string().optional(),
});

const walletTransactionActionModel = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('AddKey'),
    params: z.object({
      publicKey: z.string(),
      accessKey: z.object({
        nonce: z.number().optional(),
        permission: z.object({
          receiverId: z.string(),
          allowance: z.string().optional(),
          methodNames: z.string().array().optional(),
        }),
      }),
    }),
  }),
  z.object({
    type: z.literal('CreateAccount'),
  }),
  z.object({
    type: z.literal('DeleteAccount'),
    params: z.object({
      beneficiaryId: z.string(),
    }),
  }),
  z.object({
    type: z.literal('DeleteKey'),
    params: z.object({
      publicKey: z.string(),
    }),
  }),
  z.object({
    type: z.literal('DeployContract'),
    params: z.object({
      code: z.instanceof(Uint8Array),
    }),
  }),
  z.object({
    type: z.literal('FunctionCall'),
    params: z.object({
      methodName: z.string(),
      args: z.record(z.string(), z.unknown()).default({}),
      gas: z.string(),
      deposit: z.string(),
    }),
  }),
  z.object({
    type: z.literal('Stake'),
    params: z.object({
      stake: z.string(),
      publicKey: z.string(),
    }),
  }),
  z.object({
    type: z.literal('Transfer'),
    params: z.object({
      deposit: z.string(),
    }),
  }),
]);

export const agentNearSendTransactionsRequestModel = z.object({
  transactions: z
    .object({
      signerId: z.string().optional(),
      receiverId: z.string(),
      actions: walletTransactionActionModel.array(),
    })
    .array(),
  requestId: z.string().nullish(),
});

export const agentNearViewRequestModel = z.object({
  contractId: z.string(),
  methodName: z.string(),
  args: z.record(z.string(), z.unknown()).optional(),
  requestId: z.string().nullish(),
  blockQuery: z
    .object({
      blockId: z.string().or(z.number()),
    })
    .or(
      z.object({
        finality: z.enum(['optimistic', 'near-final', 'final']),
      }),
    )
    .or(
      z.object({
        sync_checkpoint: z.enum(['genesis', 'earliest_available']),
      }),
    )
    .optional(),
});

export const agentNearAccountRequestModel = z.object({
  accountId: z.string().nullable().default(''),
  requestId: z.string().nullish(),
});

export const agentAddSecretsRequestModel = z.object({
  secrets: z
    .object({ agentId: z.string(), key: z.string(), value: z.string() })
    .array(),
  requestId: z.string().nullish(),
  reloadAgentOnSuccess: z.boolean().default(true),
  reloadAgentMessage: z.string().nullish(),
});

export const threadMetadataModel = z
  .object({
    agent_ids: z.preprocess(
      (val) =>
        typeof val === 'string'
          ? val.split(',').map((item) => item.trim())
          : val,
      z.array(z.string()).default([]),
    ),
    topic: z.string().optional(),
  })
  .passthrough();

export const threadModel = z.object({
  id: z.string(),
  created_at: z.number(),
  object: z.string(),
  metadata: z.preprocess((value) => value ?? {}, threadMetadataModel),
});

export const threadsModel = threadModel.array();

export const threadRunModel = z.object({
  id: z.string(),
  thread_id: z.string(),
  status: z.enum([
    'queued',
    'in_progress',
    'requires_action',
    'cancelling',
    'cancelled',
    'failed',
    'completed',
    'incomplete',
    'expired',
  ]),
});

export const threadMessageMetadataModel = z.intersection(
  z
    .object({
      message_type: z.string(),
    })
    .partial(),
  z.record(z.string(), z.unknown()),
);

export const threadMessageContentModel = z.object({
  type: z.enum(['text']).or(z.string()),
  text: z
    .object({
      annotations: z.unknown().array(),
      value: z.string(),
    })
    .optional(),
});

export const threadMessageModel = z.object({
  id: z.string(),
  assistant_id: z.unknown(),
  attachments: z
    .object({
      file_id: z.string(),
      tools: z.unknown().array().nullish(),
    })
    .array()
    .nullable(),
  created_at: z.number(),
  completed_at: z.number().nullable(),
  content: threadMessageContentModel.array(),
  incomplete_at: z.number().nullable(),
  incomplete_details: z.unknown().nullable(),
  metadata: threadMessageMetadataModel.nullish(),
  object: z.string(),
  role: z.enum(['user', 'assistant', 'system']),
  run_id: z.string().nullable(),
  status: z.string(),
  thread_id: z.string(),
});

export const threadMessagesModel = z.object({
  object: z.string(),
  data: threadMessageModel.array(),
  has_more: z.boolean(),
  first_id: z.string(),
  last_id: z.string(),
});

export const threadFileModel = z.object({
  id: z.string(),
  bytes: z.number(),
  created_at: z.number(),
  filename: z.string(),
  object: z.string(),
  purpose: z.string(),
  status: z.string(),
  status_details: z.string(),
  content: z.string().default('').or(z.instanceof(Uint8Array)),
});
