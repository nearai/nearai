import mime from 'mime';
import { type z } from 'zod';

import { env } from '@/env';
import {
  threadFileModel,
  threadMessagesModel,
  threadModel,
  threadRunModel,
} from '@/lib/models';
import { filePathIsImage } from '@/utils/file';
import { createZodFetcher } from '@/utils/zod-fetch';

const fetchWithZod = createZodFetcher();

export async function fetchThreadContents({
  afterMessageId,
  authorization,
  runId,
  threadId,
}: {
  afterMessageId?: string;
  authorization: string;
  runId?: string;
  threadId: string;
}) {
  const thread = await fetchWithZod(
    threadModel,
    `${env.ROUTER_URL}/threads/${threadId}`,
    {
      headers: {
        Authorization: authorization,
      },
    },
  );

  const run = runId
    ? await fetchWithZod(
        threadRunModel,
        `${env.ROUTER_URL}/threads/${threadId}/runs/${runId}`,
        {
          headers: {
            Authorization: authorization,
          },
        },
      )
    : undefined;

  const messagesUrl = new URL(`${env.ROUTER_URL}/threads/${threadId}/messages`);
  messagesUrl.searchParams.append('limit', '1000');
  messagesUrl.searchParams.append('order', 'asc');
  if (afterMessageId) messagesUrl.searchParams.append('after', afterMessageId);
  const messages = await fetchWithZod(
    threadMessagesModel,
    messagesUrl.toString(),
    {
      headers: {
        Authorization: authorization,
      },
    },
  );

  const files = await fetchFilesAttachedToMessages(authorization, messages);

  return {
    ...thread,
    run,
    messages: messages.data,
    files,
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

      const isImage = filePathIsImage(file.filename);

      if (isImage) {
        const buffer = await contentResponse.arrayBuffer();
        const stringifiedBuffer = Buffer.from(buffer).toString('base64');
        const contentType = contentResponse.headers.get('content-type');
        const imageBase64 = `data:${contentType};base64,${stringifiedBuffer}`;
        file.content = imageBase64;
      } else if (mime.getType(file.filename) === 'application/pdf') {
        const blob = await contentResponse.blob();
        file.content = await blob.bytes();
      } else {
        const blob = await contentResponse.blob();
        file.content = await blob.text();
      }

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
