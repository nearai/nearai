import { TarReader } from '@gera2ld/tarjs';
import { z } from 'zod';
import { createZodFetcher } from 'zod-fetch';

import { env } from '~/env';
import {
  agentRequestModel,
  chatCompletionsModel,
  chatResponseModel,
  listFiles,
  listModelsResponseModel,
  listNoncesModel,
  listRegistry,
  type messageModel,
  revokeNonceModel,
} from '~/lib/models';
import {
  createTRPCRouter,
  protectedProcedure,
  publicProcedure,
} from '~/server/api/trpc';

const fetchWithZod = createZodFetcher();

export interface FileStructure {
  name: string;
  type: number;
  size: number;
  headerOffset: number;
}

export const registryCategory = z.enum([
  'agent',
  'benchmark',
  'category',
  'dataset',
  'environment',
  'model',
]);
export type RegistryCategory = z.infer<typeof registryCategory>;

async function downloadEnvironment(environmentId: string) {
  const u = `${env.ROUTER_URL}/registry/download_file`;
  const [namespace, name, version] = environmentId.split('/');

  const response = await fetch(u, {
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

  const fileStructure: FileStructure[] = [];
  const files: Record<string, string> = {};
  const environment = {
    environmentId,
    fileStructure,
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
        environment.fileStructure.push(fileInfo);
        environment.files[fileName] = tarReader.getTextFile(fileName);
      }
    }
  }

  return environment;
}

export const hubRouter = createTRPCRouter({
  listModels: publicProcedure.query(async () => {
    const u = env.ROUTER_URL + '/models';

    const response = await fetch(u);
    const data: unknown = await response.json();

    return listModelsResponseModel.parse(data);
  }),

  chat: protectedProcedure
    .input(chatCompletionsModel)
    .mutation(async ({ ctx, input }) => {
      const u = env.ROUTER_URL + '/chat/completions';

      const response = await fetch(u, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.authorization,
        },
        body: JSON.stringify(input),
      });

      if (!response.ok) {
        throw new Error(
          'Failed to send chat completions, status: ' + response.status,
        );
      }

      const data: unknown = await response.json();

      return chatResponseModel.parse(data);
    }),

  listNonces: protectedProcedure.query(async ({ ctx }) => {
    const u = env.ROUTER_URL + '/nonce/list';

    const nonces = await fetchWithZod(listNoncesModel, u, {
      headers: {
        Authorization: ctx.authorization,
      },
    });

    return nonces;
  }),

  revokeNonce: protectedProcedure
    .input(revokeNonceModel)
    .mutation(async ({ input }) => {
      const u = env.ROUTER_URL + '/nonce/revoke';

      try {
        // We can't use regular auth since we need to use the signed revoke message.
        const response = await fetch(u, {
          headers: {
            Authorization: input.auth,
            'Content-Type': 'application/json',
          },
          method: 'POST',
          body: JSON.stringify({ nonce: input.nonce }),
        });
        return response;
      } catch (e) {
        console.error(e);
        throw e;
      }
    }),

  revokeAllNonces: protectedProcedure
    .input(z.object({ auth: z.string() }))
    .mutation(async ({ input }) => {
      const u = env.ROUTER_URL + '/nonce/revoke/all';

      try {
        // We can't use regular auth since we need to use the signed revoke message.
        const response = await fetch(u, {
          headers: {
            Authorization: input.auth,
            'Content-Type': 'application/json',
          },
          method: 'POST',
        });
        return response;
      } catch (e) {
        console.error(e);
        throw e;
      }
    }),

  listRegistry: publicProcedure
    .input(
      z.object({
        category: registryCategory,
        limit: z.number().default(10_000),
        namespace: z.string().optional(),
        showLatestVersion: z.boolean().default(true),
        tags: z.string().array().optional(),
      }),
    )
    .query(async ({ input }) => {
      const url = new URL(`${env.ROUTER_URL}/registry/list_entries`);

      url.searchParams.append('category', input.category);
      url.searchParams.append('total', `${input.limit}`);
      url.searchParams.append(
        'show_latest_version',
        `${input.showLatestVersion}`,
      );

      if (input.namespace)
        url.searchParams.append('namespace', input.namespace);

      if (input.tags) url.searchParams.append('tags', input.tags.join(','));

      const list = await fetchWithZod(listRegistry, url.toString(), {
        method: 'POST',
      });

      return list;
    }),

  loadEnvironment: protectedProcedure
    .input(z.object({ environmentId: z.string() }))
    .query(async ({ input }) => {
      return await downloadEnvironment(input.environmentId);
    }),

  listFilePaths: publicProcedure
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

  loadFileByPath: publicProcedure
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

  agentChat: protectedProcedure
    .input(agentRequestModel)
    .mutation(async ({ ctx, input }) => {
      const u = env.ROUTER_URL + '/agent/runs';

      const response = await fetch(u, {
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

      const responseText: string = await response.text();
      if (!responseText.match(/".*\/.*\/.*/)) {
        // check whether the response matches namespace/name/version
        throw new Error('Response text does not match namespace/name/version');
      }

      const environmentId = responseText.replace(/\\/g, '').replace(/"/g, '');

      return downloadEnvironment(environmentId);
    }),
});
