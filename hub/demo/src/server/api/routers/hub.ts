import { TarReader } from '@gera2ld/tarjs';
import { z } from 'zod';
import { createZodFetcher } from 'zod-fetch';

import { env } from '~/env';
import {
  agentRequestModel,
  chatCompletionsModel,
  chatResponseModel,
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
  'model',
]);
export type RegistryCategory = z.infer<typeof registryCategory>;

export const hubRouter = createTRPCRouter({
  listModels: publicProcedure.query(async () => {
    const u = env.ROUTER_URL + '/models';

    const response = await fetch(u);
    const resp: unknown = await response.json();

    return listModelsResponseModel.parse(resp);
  }),

  chat: protectedProcedure
    .input(chatCompletionsModel)
    .mutation(async ({ ctx, input }) => {
      const u = env.ROUTER_URL + '/chat/completions';

      const response = await fetch(u, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.Authorization!,
        },
        body: JSON.stringify(input),
      });

      // check for errors
      if (!response.ok) {
        throw new Error(
          'Failed to send chat completions, status: ' +
            response.status +
            ' ' +
            response.statusText,
        );
      }

      const resp: unknown = await response.json();

      return chatResponseModel.parse(resp);
    }),

  listNonces: protectedProcedure.query(async ({ ctx }) => {
    const u = env.ROUTER_URL + '/nonce/list';

    const resp = await fetchWithZod(listNoncesModel, u, {
      headers: {
        Authorization: ctx.Authorization!,
      },
    });

    return resp;
  }),

  revokeNonce: protectedProcedure
    .input(revokeNonceModel)
    .mutation(async ({ input }) => {
      const u = env.ROUTER_URL + '/nonce/revoke';

      try {
        // We can't use regular auth since we need to use the signed revoke message.
        const resp = await fetch(u, {
          headers: {
            Authorization: input.auth,
            'Content-Type': 'application/json',
          },
          method: 'POST',
          body: JSON.stringify({ nonce: input.nonce }),
        });
        return resp;
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
        const resp = await fetch(u, {
          headers: {
            Authorization: input.auth,
            'Content-Type': 'application/json',
          },
          method: 'POST',
        });
        return resp;
      } catch (e) {
        console.error(e);
        throw e;
      }
    }),

  listRegistry: publicProcedure
    .input(
      z.object({
        category: registryCategory,
      }),
    )
    .query(async ({ input }) => {
      const limit = 1000;
      const u =
        env.ROUTER_URL +
        `/registry/list_entries?category=${input.category}&total=${limit}`;

      const resp = await fetchWithZod(listRegistry, u, {
        method: 'POST',
      });

      return resp;
    }),

  agentChat: protectedProcedure
    .input(agentRequestModel)
    .mutation(async ({ ctx, input }) => {
      const u = env.ROUTER_URL + '/agent/runs';

      const response = await fetch(u, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: ctx.Authorization!,
        },
        body: JSON.stringify(input),
      });

      if (!response.ok) {
        throw new Error(
          'Failed to send chat completions, status: ' +
            response.status +
            ' ' +
            response.statusText,
        );
      }

      const responseText: string = await response.text();
      if (!responseText.match(/".*\/.*\/.*/)) {
        // check whether the response matches namespace/name/version
        throw new Error('Failed to run agent, response: ' + responseText);
      }

      const environmentName = responseText.replace(/\\/g, '').replace(/"/g, '');

      const u2 = `${env.ROUTER_URL}/registry/download_file`;
      const [namespace, name, version] = environmentName.split('/');

      const resp = await fetch(u2, {
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

      if (!resp.ok) {
        console.error(
          'Requested Environment is: ',
          `${namespace}/${name}/${version}`,
        );
        throw new Error(
          'Failed to download environment, status: ' +
            resp.status +
            ' ' +
            resp.statusText,
        );
      }
      if (!resp.body) {
        throw new Error('Response body is null');
      }

      const stream = resp.body.pipeThrough(new DecompressionStream('gzip'));
      const blob = await new Response(stream).blob();
      const tarReader = await TarReader.load(blob);

      const chat = tarReader
        .getTextFile('./chat.txt')
        .split('\n')
        .filter((message) => message)
        .map((message) => {
          return JSON.parse(message) as z.infer<typeof messageModel>;
        });

      const fileStructure: FileStructure[] = [];
      const files: Record<string, string> = {};
      const environment = {
        environmentName: environmentName,
        fileStructure,
        files,
        chat,
      };

      for (const fileInfo of tarReader.fileInfos) {
        if ((fileInfo.type as number) === 48) {
          // Actual file type differs from TarFileType enum. Files are coming through as 48.

          const fileName = fileInfo.name.replace(/^\.\//, '');

          if (fileName !== 'chat.txt' && fileName !== '.next_action') {
            fileInfo.name = fileName;
            environment.fileStructure.push(fileInfo);
            environment.files[fileName] = tarReader.getTextFile(fileName);
          }
        }
      }

      return environment;
    }),
});
