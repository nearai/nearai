import path from 'path';
import { z } from 'zod';
import { createZodFetcher } from 'zod-fetch';

import { env } from '~/env';
import {
  chatResponseModel,
  chatWithAgentModel,
  chatWithModelModel,
  type entriesModel,
  entryCategory,
  entryModel,
  entrySecretModel,
  evaluationsTableModel,
  filesModel,
  modelsModel,
  noncesModel,
  revokeNonceModel,
  threadMessagesModel,
  threadMetadataModel,
  threadsModel,
} from '~/lib/models';
import {
  createTRPCRouter,
  protectedProcedure,
  publicProcedure,
} from '~/server/api/trpc';
import { loadEntriesFromDirectory } from '~/server/utils/data-source';
import { loadAttachmentFilesForMessages } from '~/server/utils/files';
import { runMessageOnAgentThread } from '~/server/utils/threads';

const fetchWithZod = createZodFetcher();

export const hubRouter = createTRPCRouter({
  chatWithAgent: protectedProcedure
    .input(chatWithAgentModel)
    .mutation(async ({ ctx, input }) => {
      const { threadId } = await runMessageOnAgentThread(
        ctx.authorization,
        input,
      );

      return {
        threadId,
      };
    }),

  chatWithModel: protectedProcedure
    .input(chatWithModelModel)
    .mutation(async ({ ctx, input }) => {
      const url = `${env.ROUTER_URL}/chat/completions`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.authorization,
        },
        body: JSON.stringify(input),
      });

      const data: unknown = await response.json();
      if (!response.ok) throw data;

      return chatResponseModel.parse(data);
    }),

  entries: publicProcedure
    .input(
      z.object({
        category: entryCategory.optional(),
        limit: z.number().default(10_000),
        namespace: z.string().optional(),
        showLatestVersion: z.boolean().default(true),
        starredBy: z.string().optional(),
        tags: z.string().array().optional(),
      }),
    )
    .query(async ({ ctx, input }) => {
      const url = new URL(`${env.ROUTER_URL}/registry/list_entries`);

      url.searchParams.append('total', `${input.limit}`);
      url.searchParams.append(
        'show_latest_version',
        `${input.showLatestVersion}`,
      );

      if (input.category) url.searchParams.append('category', input.category);

      if (input.namespace)
        url.searchParams.append('namespace', input.namespace);

      if (input.tags) url.searchParams.append('tags', input.tags.join(','));

      if (input.category == 'agent' && env.DATA_SOURCE == 'local_files') {
        if (!env.HOME)
          throw new Error(
            'Missing required HOME environment variable for serving local files',
          );
        const registryPath = path.join(env.HOME, '.nearai', 'registry');
        return await loadEntriesFromDirectory(registryPath);
      }

      if (input.starredBy) {
        url.searchParams.append('starred_by', input.starredBy);
      }

      if (ctx.signature) {
        url.searchParams.append('star_point_of_view', ctx.signature.account_id);
      }

      const response = await fetch(url.toString(), {
        method: 'POST',
      });

      const data: unknown = await response.json();

      if (!response.ok || !Array.isArray(data)) throw data;

      /*
        Unfortunately, we can't rely on fetchWithZod() for this method. If the endpoint 
        returns a single record that didn't match our expected "entries" schema, 
        all of the data would be thrown out. Instead, we loop over each returned item and 
        parse the entries one at a time - only omitting entries that aren't valid instead 
        of throwing an error for the entire list.
      */

      const list: z.infer<typeof entriesModel> = data
        .map((item) => {
          const parsed = entryModel.safeParse(item);
          return parsed.data;
        })
        .filter((entry) => !!entry);

      return list;
    }),

  evaluations: publicProcedure.query(async () => {
    const evaluations = await fetchWithZod(
      evaluationsTableModel,
      `${env.ROUTER_URL}/evaluation/table`,
    );

    const infoColumns = ['agent', 'model', 'namespace', 'version', 'provider'];
    const benchmarkColumns = evaluations.columns.filter(
      (column) => !infoColumns.includes(column),
    );

    evaluations.rows.forEach((row) => {
      if (row.agent && row.namespace && row.version) {
        row.agentId = `${row.namespace}/${row.agent}/${row.version}`;
      }
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
        filePath: z.string(),
        namespace: z.string(),
        name: z.string(),
        version: z.string(),
      }),
    )
    .query(async ({ input }) => {
      const response = await fetch(`${env.ROUTER_URL}/registry/download_file`, {
        method: 'POST',
        headers: {
          Accept: 'binary/octet-stream',
          'Content-Type': 'application/json',
        },
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

      const content = await (await response.blob()).text();

      return {
        content,
        path: input.filePath,
      };
    }),

  filePaths: publicProcedure
    .input(
      z.object({
        namespace: z.string(),
        name: z.string(),
        version: z.string(),
      }),
    )
    .query(async ({ input }) => {
      const files = await fetchWithZod(
        filesModel,
        `${env.ROUTER_URL}/registry/list_files`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
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

  models: publicProcedure.query(async () => {
    const url = `${env.ROUTER_URL}/models`;

    const response = await fetch(url);
    const data: unknown = await response.json();

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

      const data: unknown = await response.json();
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

      const data: unknown = await response.json();
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
      url.searchParams.append('offset', `${input.offset}`);

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
        version: z.string(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const url = `${env.ROUTER_URL}/create_hub_secret`;

      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.authorization,
        },
        method: 'POST',
        body: JSON.stringify(input),
      });

      const data: unknown = await response.json();
      if (!response.ok) throw data;

      return true;
    }),

  removeSecret: protectedProcedure
    .input(
      z.object({
        category: entryCategory.optional(),
        key: z.string(),
        name: z.string(),
        namespace: z.string(),
        version: z.string().optional(),
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

      const data: unknown = await response.json();
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

      const data: unknown = await response.json();
      if (!response.ok) throw data;

      return true;
    }),

  thread: protectedProcedure
    .input(
      z.object({
        threadId: z.string(),
      }),
    )
    .query(async ({ ctx, input }) => {
      const url = new URL(
        `${env.ROUTER_URL}/threads/${input.threadId}/messages`,
      );
      url.searchParams.append('limit', '1000');
      url.searchParams.append('order', 'asc');

      const messages = await fetchWithZod(threadMessagesModel, url.toString(), {
        headers: {
          Authorization: ctx.authorization,
        },
      });

      const files = await loadAttachmentFilesForMessages(
        ctx.authorization,
        messages,
      );

      return {
        id: input.threadId,
        files,
        messages: messages.data,
      };
    }),

  threads: protectedProcedure.query(async ({ ctx }) => {
    const url = `${env.ROUTER_URL}/threads`;

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

        const data: unknown = await response.json();
        if (!response.ok) throw data;

        return true;
      },
    ),
});
