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
  revokeNonceModel,
} from '~/lib/models';
import {
  createTRPCRouter,
  protectedProcedure,
  publicProcedure,
} from '~/server/api/trpc';
import { TarReader } from '@gera2ld/tarjs';

const fetchWithZod = createZodFetcher();

export interface FileStructure {
  name: string;
  type: number;
  size: number;
  headerOffset: number;
}

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
    .input(z.object({ category: z.string() }))
    .query(async ({ input }) => {
      const u =
        env.ROUTER_URL + '/registry/list_entries?category=' + input.category;

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
      return await fetch(u2, {
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
      })
        .then(async (resp) => {
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
          return resp.body.pipeThrough(new DecompressionStream('gzip'));
        })
        .then((decompressedStream) => new Response(decompressedStream).blob())
        .then((blob) => TarReader.load(blob))
        .then((tarReader) => {
          const rawChat = tarReader.getTextFile('./chat.txt');
          const parsedChat = rawChat
            .split('\n')
            .filter((message) => message)
            .map((message) => {
              console.log(message);
              return JSON.parse(message);
            });

          const fileStructure: FileStructure[] = [];
          const files: Record<string, string> = {};
          const environment = {
            environmentName: environmentName,
            fileStructure,
            files,
            chat: parsedChat,
          };
          for (const fileInfo of tarReader.fileInfos) {
            // @ts-ignore // actual file type differs from TarFileType enum
            if (fileInfo.type === 48) {
              // files are coming through as 48
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
        });
    }),
});
