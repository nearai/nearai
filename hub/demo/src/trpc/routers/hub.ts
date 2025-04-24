import { parseStringOrNumber } from '@nearai/ui/utils';
import { z } from 'zod';

import {
  AITP_CAPABILITIES,
  AITP_CLIENT_ID,
} from '@/components/threads/messages/aitp/schema';
import { env } from '@/env';
import { rawFileUrlForEntry } from '@/lib/entries';
import {
  chatWithAgentModel,
  entryCategory,
  entryFilesModel,
  entryModel,
  entrySecretModel,
  evaluationsTableModel,
  modelsModel,
  noncesModel,
  optionalVersion,
  revokeNonceModel,
  threadMessageModel,
  threadMetadataModel,
  threadModel,
  threadRunModel,
  threadsModel,
} from '@/lib/models';
import { conditionallyIncludeAuthorizationHeader } from '@/trpc/utils/headers';
import { conditionallyRemoveSecret } from '@/trpc/utils/secrets';
import { fetchThreadContents } from '@/trpc/utils/threads';
import { filePathIsImage } from '@/utils/file';
import { createZodFetcher } from '@/utils/zod-fetch';

import { createTRPCRouter, protectedProcedure, publicProcedure } from '../trpc';
import {
  fetchEntries,
  fetchEntriesInputSchema,
  fetchEntry,
  fetchEntryInputSchema,
  fetchEntryMetadataJson,
} from '../utils/entries';
import { generateMockedAITPMessages } from '../utils/mock-aitp';

const fetchWithZod = createZodFetcher();

export const hubRouter = createTRPCRouter({
  entries: publicProcedure
    .input(fetchEntriesInputSchema)
    .query(async ({ ctx, input }) => {
      const entries = await fetchEntries(ctx, input);
      return entries;
    }),

  entry: publicProcedure
    .input(fetchEntryInputSchema)
    .query(async ({ ctx, input }) => {
      const entries = await fetchEntry(ctx, input);
      return entries;
    }),

  evaluations: publicProcedure
    .input(
      z
        .object({
          page: z.string().optional(),
        })
        .optional(),
    )
    .query(async ({ input }) => {
      const url = new URL(`${env.ROUTER_URL}/evaluation/table`);

      if (input?.page) url.searchParams.set('page', input.page);

      const evaluations = await fetchWithZod(evaluationsTableModel, url);

      const infoColumns = [
        'agent',
        'model',
        'namespace',
        'version',
        'provider',
      ];
      const benchmarkColumns = evaluations.columns.filter(
        (column) => !infoColumns.includes(column),
      );

      evaluations.rows.forEach((row) => {
        if (row.namespace && row.version) {
          if (row.agent) {
            row.agentId = `${row.namespace}/${row.agent}/${row.version}`;
          } else if (row.model && row.provider === 'local') {
            row.modelId = `${row.namespace}/${row.model}/${row.version}`;
          }
        }

        benchmarkColumns.forEach((key) => {
          if (row[key]) {
            row[key] = parseStringOrNumber(row[key]);
          }
        });
      });

      const defaultBenchmarkColumns = evaluations.important_columns.filter(
        (column) => !infoColumns.includes(column),
      );

      return {
        benchmarkColumns,
        defaultBenchmarkColumns,
        infoColumns,
        results: evaluations.rows,
      };
    }),

  file: publicProcedure
    .input(
      z.object({
        category: entryCategory,
        filePath: z.string(),
        namespace: z.string(),
        name: z.string(),
        version: z.string(),
      }),
    )
    .query(async ({ ctx, input }) => {
      const isImage = filePathIsImage(input.filePath);

      if (isImage) {
        return {
          content: rawFileUrlForEntry(input, input.filePath),
          path: input.filePath,
        };
      }

      if (input.filePath === 'metadata.json') {
        const metadata = await fetchEntryMetadataJson(ctx, input);
        return {
          content: metadata.stringified,
          path: input.filePath,
        };
      }

      const response = await fetch(`${env.ROUTER_URL}/registry/download_file`, {
        method: 'POST',
        headers: conditionallyIncludeAuthorizationHeader(ctx.authorization, {
          Accept: 'binary/octet-stream',
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({
          entry_location: {
            namespace: input.namespace,
            name: input.name,
            version: input.version,
          },
          path: input.filePath,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to load file, status: ${response.status}`);
      }

      const blob = await response.blob();
      const content = await blob.text();

      return {
        content,
        path: input.filePath,
      };
    }),

  filePaths: publicProcedure
    .input(
      z.object({
        category: entryCategory,
        namespace: z.string(),
        name: z.string(),
        version: z.string(),
      }),
    )
    .query(async ({ ctx, input }) => {
      const files = await fetchWithZod(
        entryFilesModel,
        `${env.ROUTER_URL}/registry/list_files`,
        {
          method: 'POST',
          headers: conditionallyIncludeAuthorizationHeader(ctx.authorization, {
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({
            entry_location: {
              namespace: input.namespace,
              name: input.name,
              version: input.version,
            },
          }),
        },
      );

      const paths = files.flatMap((file) => file.filename);
      paths.push('metadata.json');
      paths.sort();

      return paths;
    }),

  detailsForFileUpload: protectedProcedure.query(({ ctx }) => {
    // This endpoint gives the frontend the details it needs to upload a file to the Hub API directly
    return {
      authorization: ctx.authorization,
      routerUrl: env.ROUTER_URL,
    };
  }),

  models: publicProcedure.query(async () => {
    const url = `${env.ROUTER_URL}/models`;

    const response = await fetch(url);
    const data: unknown = await response.json().catch(() => response.text());

    return modelsModel.parse(data);
  }),

  nonces: protectedProcedure.query(async ({ ctx }) => {
    const url = `${env.ROUTER_URL}/nonce/list`;

    const nonces = await fetchWithZod(noncesModel, url, {
      headers: {
        Authorization: ctx.authorization,
      },
    });

    return nonces;
  }),

  revokeNonce: protectedProcedure
    .input(revokeNonceModel)
    .mutation(async ({ input }) => {
      const url = `${env.ROUTER_URL}/nonce/revoke`;

      // We can't use regular auth since we need to use the signed revoke message.
      const response = await fetch(url, {
        headers: {
          Authorization: input.auth,
          'Content-Type': 'application/json',
        },
        method: 'POST',
        body: JSON.stringify({ nonce: input.nonce }),
      });

      const data: unknown = await response.json().catch(() => response.text());
      if (!response.ok) throw data;

      return data;
    }),

  revokeAllNonces: protectedProcedure
    .input(z.object({ auth: z.string() }))
    .mutation(async ({ input }) => {
      const url = `${env.ROUTER_URL}/nonce/revoke/all`;

      // We can't use regular auth since we need to use the signed revoke message.
      const response = await fetch(url, {
        headers: {
          Authorization: input.auth,
          'Content-Type': 'application/json',
        },
        method: 'POST',
      });

      const data: unknown = await response.json().catch(() => response.text());
      if (!response.ok) throw data;

      return data;
    }),

  secrets: protectedProcedure
    .input(
      z.object({
        limit: z.number().default(10_000),
        offset: z.number().default(0),
      }),
    )
    .query(async ({ ctx, input }) => {
      const url = new URL(`${env.ROUTER_URL}/get_user_secrets`);
      url.searchParams.append('limit', `${input.limit}`);

      const secrets = await fetchWithZod(
        entrySecretModel.array(),
        url.toString(),
        {
          headers: {
            Authorization: ctx.authorization,
          },
        },
      );

      return secrets;
    }),

  addSecret: protectedProcedure
    .input(
      z.object({
        category: entryCategory,
        description: z.string().optional().default(''),
        key: z.string(),
        name: z.string(),
        namespace: z.string(),
        value: z.string(),
        version: optionalVersion,
      }),
    )
    .mutation(async ({ ctx, input }) => {
      /*
        If there's an existing secret that would create a conflict, 
        remove it before adding it again to avoid the Hub API throwing 
        an error. We might want to consider adding proper upsert support 
        on the Hub API side when we have time.
      */

      await conditionallyRemoveSecret(ctx.authorization, input);

      const url = `${env.ROUTER_URL}/create_hub_secret`;

      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.authorization,
        },
        method: 'POST',
        body: JSON.stringify(input),
      });

      const data: unknown = await response.json().catch(() => response.text());
      if (!response.ok) throw data;

      return true;
    }),

  removeSecret: protectedProcedure
    .input(
      z.object({
        category: entryCategory,
        key: z.string(),
        name: z.string(),
        namespace: z.string(),
        version: optionalVersion,
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const url = `${env.ROUTER_URL}/remove_hub_secret`;

      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.authorization,
        },
        method: 'POST',
        body: JSON.stringify(input),
      });

      const data: unknown = await response.json().catch(() => response.text());
      if (!response.ok) throw data;

      return true;
    }),

  starEntry: protectedProcedure
    .input(
      z.object({
        action: z.enum(['add', 'remove']),
        namespace: z.string(),
        name: z.string(),
      }),
    )
    .mutation(async ({ ctx, input: { action, namespace, name } }) => {
      const url =
        env.ROUTER_URL +
        `/stars/${action === 'add' ? 'add_star' : 'remove_star'}`;

      const formData = new FormData();
      formData.append('namespace', namespace);
      formData.append('name', name);

      const response = await fetch(url, {
        headers: {
          Authorization: ctx.authorization,
        },
        method: 'POST',
        body: formData,
      });

      const data: unknown = await response.json().catch(() => response.text());
      if (!response.ok) throw data;

      return true;
    }),

  forkEntry: protectedProcedure
    .input(
      z.object({
        modifications: z.object({
          name: z.string(),
          version: z.string().nullish(),
          description: z.string().nullish(),
        }),
        namespace: z.string(),
        name: z.string(),
        version: z.string(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const response = await fetch(`${env.ROUTER_URL}/registry/fork`, {
        method: 'POST',
        headers: {
          Authorization: ctx.authorization,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          modifications: input.modifications,
          entry_location: {
            namespace: input.namespace,
            name: input.name,
            version: input.version,
          },
        }),
      });

      const data: unknown = await response.json().catch(() => response.text());
      if (!response.ok) throw data;

      return z
        .object({
          status: z.string(),
          entry: z.object({
            namespace: z.string(),
            name: z.string(),
            version: z.string(),
          }),
        })
        .parse(data);
    }),

  thread: protectedProcedure
    .input(
      z.object({
        afterMessageId: z.string().optional(),
        mockedAitpMessages: z.boolean().default(false),
        runId: z.string().optional(),
        threadId: z.string(),
      }),
    )
    .query(async ({ ctx, input }) => {
      const contents = await fetchThreadContents({
        ...input,
        authorization: ctx.authorization,
      });

      if (input.mockedAitpMessages) {
        contents.messages = [
          ...contents.messages,
          ...generateMockedAITPMessages(input.threadId),
        ];
      }

      return contents;
    }),

  chatWithAgent: protectedProcedure
    .input(chatWithAgentModel)
    .mutation(async ({ ctx, input }) => {
      if (typeof input.max_iterations !== 'number') {
        input.max_iterations = 1;
      }

      const thread = input.thread_id
        ? await fetchWithZod(
            threadModel,
            `${env.ROUTER_URL}/threads/${input.thread_id}`,
            {
              headers: {
                Authorization: ctx.authorization,
              },
            },
          )
        : await fetchWithZod(threadModel, `${env.ROUTER_URL}/threads`, {
            method: 'POST',
            headers: {
              Authorization: ctx.authorization,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              metadata: {
                actors: JSON.stringify([
                  {
                    id: ctx.signature.account_id,
                    client_id: AITP_CLIENT_ID,
                    capabilities: AITP_CAPABILITIES,
                  },
                ]),
              },
            }),
          });

      const message = await fetchWithZod(
        threadMessageModel,
        `${env.ROUTER_URL}/threads/${thread.id}/messages`,
        {
          method: 'POST',
          headers: {
            Authorization: ctx.authorization,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            attachments: input.attachments,
            content: input.new_message,
            role: 'user',
          }),
        },
      );

      const run = await fetchWithZod(
        threadRunModel,
        `${env.ROUTER_URL}/threads/${thread.id}/runs`,
        {
          method: 'POST',
          headers: {
            Authorization: ctx.authorization,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            agent_env_vars: input.agent_env_vars,
            assistant_id: input.agent_id,
            max_iterations: input.max_iterations,
            thread_id: thread.id,
            user_env_vars: input.user_env_vars,
          }),
        },
      );

      return {
        thread,
        message,
        run,
      };
    }),

  threadContents: protectedProcedure
    .input(
      z.object({
        afterMessageId: z.string().optional(),
        threadId: z.string(),
      }),
    )
    .query(async ({ ctx, input }) => {
      const contents = await fetchThreadContents({
        ...input,
        authorization: ctx.authorization,
      });

      return contents;
    }),

  threads: protectedProcedure.query(async ({ ctx }) => {
    const url = `${env.ROUTER_URL}/threads?include_subthreads=false`;

    const threads = await fetchWithZod(threadsModel, url, {
      headers: {
        Authorization: ctx.authorization,
      },
    });

    threads.sort((a, b) => b.created_at - a.created_at);

    return threads;
  }),

  removeThread: protectedProcedure
    .input(
      z.object({
        threadId: z.string(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      await fetch(`${env.ROUTER_URL}/threads/${input.threadId}`, {
        method: 'DELETE',
        headers: {
          Authorization: ctx.authorization,
        },
      });

      return true;
    }),

  updateThread: protectedProcedure
    .input(
      z.object({
        threadId: z.string(),
        metadata: threadMetadataModel,
      }),
    )
    .mutation(async ({ ctx, input }) => {
      await fetch(`${env.ROUTER_URL}/threads/${input.threadId}`, {
        method: 'POST',
        headers: {
          Authorization: ctx.authorization,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metadata: input.metadata,
        }),
      });

      return true;
    }),

  updateMetadata: protectedProcedure
    .input(
      z.object({
        namespace: z.string(),
        name: z.string(),
        version: z.string(),
        metadata: entryModel.partial(),
      }),
    )
    .mutation(
      async ({ ctx, input: { name, namespace, version, metadata } }) => {
        const response = await fetch(
          `${env.ROUTER_URL}/registry/upload_metadata`,
          {
            headers: {
              Authorization: ctx.authorization,
              'Content-Type': 'application/json',
            },
            method: 'POST',
            body: JSON.stringify({
              metadata,
              entry_location: {
                namespace,
                name,
                version,
              },
            }),
          },
        );

        const data: unknown = await response
          .json()
          .catch(() => response.text());
        if (!response.ok) throw data;

        return true;
      },
    ),
});
