import { type z } from 'zod';
import { createZodFetcher } from 'zod-fetch';

import { env } from '~/env';
import { threadFileModel, type threadMessagesModel } from '~/lib/models';

const fetchWithZod = createZodFetcher();

export async function loadAttachmentFilesForMessages(
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
