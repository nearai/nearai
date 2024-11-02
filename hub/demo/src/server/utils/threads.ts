import { type z } from 'zod';
import { createZodFetcher } from 'zod-fetch';

import { env } from '~/env';
import {
  type chatWithAgentModel,
  runModel,
  threadFileModel,
  threadMessagesModel,
  threadModel,
} from '~/lib/models';
import { poll } from '~/utils/poll';

const fetchWithZod = createZodFetcher();

export async function fetchThreadMessagesAndFiles(
  authorization: string,
  threadId: string,
) {
  const url = new URL(`${env.ROUTER_URL}/threads/${threadId}/messages`);
  url.searchParams.append('limit', '1000');
  url.searchParams.append('order', 'asc');

  const messages = await fetchWithZod(threadMessagesModel, url.toString(), {
    headers: {
      Authorization: authorization,
    },
  });

  const files = await fetchFilesAttachedToMessages(authorization, messages);

  return {
    id: threadId,
    files,
    messages: messages.data,
  };
}

export async function runMessageOnAgentThread(
  authorization: string,
  input: z.infer<typeof chatWithAgentModel>,
) {
  const thread = input.thread_id
    ? await fetchWithZod(
        threadModel,
        `${env.ROUTER_URL}/threads/${input.thread_id}`,
        {
          headers: {
            Authorization: authorization,
          },
        },
      )
    : await fetchWithZod(threadModel, `${env.ROUTER_URL}/threads`, {
        method: 'POST',
        headers: {
          Authorization: authorization,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

  await fetch(`${env.ROUTER_URL}/threads/${thread.id}/messages`, {
    method: 'POST',
    headers: {
      Authorization: authorization,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content: input.new_message,
      role: 'user',
    }),
  });

  const createdRun = await fetchWithZod(
    runModel,
    `${env.ROUTER_URL}/threads/${thread.id}/runs`,
    {
      method: 'POST',
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        thread_id: thread.id,
        assistant_id: input.agent_id,
        instructions: 'You are a helpful assistant. Complete the given task.',
        model: 'fireworks::accounts/fireworks/models/llama-v3p1-405b-instruct',
      }),
    },
  );

  await poll(
    `${env.ROUTER_URL}/threads/${thread.id}/runs/${createdRun.id}`,
    {
      headers: {
        Authorization: authorization,
        'Content-Type': 'application/json',
      },
    },
    {
      attemptDelayMs: 1000,
      maxAttempts: 60,
      // 1 minute of polling...
    },
    async (response, currentAttempt) => {
      const data = (await response.json()) as unknown;

      if (env.NODE_ENV === 'development') {
        // When running locally, this log statement can be useful
        console.log(`Polling thread run - attempt ${currentAttempt}`, data);
      }

      const run = runModel.parse(data);
      if (run.status !== 'in_progress' && run.status !== 'queued') {
        return run;
      }
    },
  );

  return {
    threadId: thread.id,
  };
}

async function fetchFilesAttachedToMessages(
  authorization: string,
  messages: z.infer<typeof threadMessagesModel>,
) {
  const threadId = messages.data[0]?.thread_id;
  const fileIds = messages.data
    .flatMap((message) =>
      message.attachments?.map((attachment) => attachment.file_id),
    )
    .filter((value) => typeof value !== 'undefined');

  const filesByPath: Record<string, z.infer<typeof threadFileModel>> = {};

  for (const fileId of fileIds) {
    try {
      const file = await fetchWithZod(
        threadFileModel,
        `${env.ROUTER_URL}/files/${fileId}`,
        {
          headers: {
            Authorization: authorization,
          },
        },
      );

      const contentResponse = await fetch(
        `${env.ROUTER_URL}/files/${fileId}/content`,
        {
          headers: {
            Accept: 'binary/octet-stream',
            Authorization: authorization,
          },
        },
      );

      file.content = await (await contentResponse.blob()).text();

      const existingFile = filesByPath[file.filename];
      if (existingFile) {
        console.warn(
          `Unique files with identical filenames detected for ${file.filename} in thread ${threadId}. File ids: ${existingFile.id}, ${file.id}. The most recent attachment will be displayed to the user.`,
        );
      }

      filesByPath[file.filename] = file;
    } catch (error) {
      console.error(`Failed to fetch fileId ${fileId}`, error);
    }
  }

  return Object.values(filesByPath);
}
