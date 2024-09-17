import { TarReader } from '@gera2ld/tarjs';
import { z } from 'zod';
import { createZodFetcher } from 'zod-fetch';

import { env } from '~/env';
import {
  chatModel,
  chatResponseModel,
  chatWithAgentModel,
  listFiles,
  listModelsResponseModel,
  listNoncesModel,
  type messageModel,
  type registryEntries,
  registryEntry,
  revokeNonceModel,
} from '~/lib/models';
import {
  createTRPCRouter,
  protectedProcedure,
  publicProcedure,
} from '~/server/api/trpc';

const fetchWithZod = createZodFetcher();

type RegistryFile = {
  content: string;
  name: string;
  type: number;
  size: number;
  headerOffset: number;
};

export const registryCategory = z.enum([
  'agent',
  'benchmark',
  'dataset',
  'environment',
  'model',
]);
export type RegistryCategory = z.infer<typeof registryCategory>;

async function downloadEnvironment(environmentId: string) {
  const url = `${env.ROUTER_URL}/registry/download_file`;
  const [namespace, name, version] = environmentId.split('/');

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'binary/octet-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      entry_location: {
        namespace,
        name,
        version,
      },
      path: 'environment.tar.gz',
    }),
  });

  if (!response.ok) {
    throw new Error(
      `Failed to download environment for ${namespace}/${name}/${version} - status: ${response.status}`,
    );
  }
  if (!response.body) {
    throw new Error('Response body is null');
  }

  const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
  const blob = await new Response(stream).blob();
  const tarReader = await TarReader.load(blob);

  const conversation = tarReader
    .getTextFile('./chat.txt')
    .split('\n')
    .filter((message) => message)
    .map((message) => {
      return JSON.parse(message) as z.infer<typeof messageModel>;
    });

  const files: Record<string, RegistryFile> = {};
  const environment = {
    environmentId,
    files,
    conversation,
  };

  for (const fileInfo of tarReader.fileInfos) {
    if ((fileInfo.type as number) === 48) {
      // Files are actually coming through as 48
      const originalFileName = fileInfo.name;
      const fileName = originalFileName.replace(/^\.\//, '');
      if (fileName !== 'chat.txt' && fileName !== '.next_action') {
        fileInfo.name = fileName;
        environment.files[fileName] = {
          ...fileInfo,
          content: tarReader.getTextFile(fileName),
        };
      }
    }
  }

  return environment;
}

export const hubRouter = createTRPCRouter({
  chat: protectedProcedure.input(chatModel).mutation(async ({ ctx, input }) => {
    const url = env.ROUTER_URL + '/chat/completions';

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

  chatWithAgent: protectedProcedure
    .input(chatWithAgentModel)
    .mutation(async ({ ctx, input }) => {
      const url = env.ROUTER_URL + '/agent/runs';

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.authorization,
        },
        body: JSON.stringify(input),
      });

      if (!response.ok) {
        throw new Error(
          `Failed to send chat completions, status: ${response.status}`,
        );
      }

      const text: string = await response.text();
      if (!text.match(/".*\/.*\/.*/)) {
        // check whether the response matches namespace/name/version
        throw new Error('Response text does not match namespace/name/version');
      }

      const environmentId = text.replace(/\\/g, '').replace(/"/g, '');

      const environment = await downloadEnvironment(environmentId);

      return environment;
    }),

  environment: protectedProcedure
    .input(z.object({ environmentId: z.string() }))
    .query(async ({ input }) => {
      return await downloadEnvironment(input.environmentId);
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
      const list = await fetchWithZod(
        listFiles,
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

      const paths = list.flatMap((file) => file.filename);
      paths.push('metadata.json');
      paths.sort();

      return paths;
    }),

  models: publicProcedure.query(async () => {
    const url = env.ROUTER_URL + '/models';

    const response = await fetch(url);
    const data: unknown = await response.json();

    return listModelsResponseModel.parse(data);
  }),

  nonces: protectedProcedure.query(async ({ ctx }) => {
    const url = env.ROUTER_URL + '/nonce/list';

    const nonces = await fetchWithZod(listNoncesModel, url, {
      headers: {
        Authorization: ctx.authorization,
      },
    });

    return nonces;
  }),

  registryEntries: publicProcedure
    .input(
      z.object({
        category: registryCategory.optional(),
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
        returns a single record that didn't match our expected "registryEntries" schema, 
        all of the data would be thrown out. Instead, we loop over each returned item and 
        parse the entries one at a time - only omitting entries that aren't valid instead 
        of throwing an error for the entire list.
      */

      const list: z.infer<typeof registryEntries> = data
        .map((item) => {
          const parsed = registryEntry.safeParse(item);
          return parsed.data;
        })
        .filter((entry) => !!entry);

      return list;
    }),

  revokeNonce: protectedProcedure
    .input(revokeNonceModel)
    .mutation(async ({ input }) => {
      const url = env.ROUTER_URL + '/nonce/revoke';

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
      const url = env.ROUTER_URL + '/nonce/revoke/all';

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

  starRegistryEntry: protectedProcedure
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

  updateMetadata: protectedProcedure
    .input(
      z.object({
        namespace: z.string(),
        name: z.string(),
        version: z.string(),
        metadata: registryEntry.partial(),
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
