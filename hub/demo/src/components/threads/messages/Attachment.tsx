'use client';

import { Flex, Placeholder, SvgIcon, Text } from '@nearai/ui';
import { formatBytes } from '@nearai/ui/utils';
import { File, FilePdf } from '@phosphor-icons/react/dist/ssr';
import mime from 'mime';
import type { z } from 'zod';

import type { threadMessageModel } from '@/lib/models';
import { useThreadsStore } from '@/stores/threads';
import { filePathIsImage } from '@/utils/file';

import { useThreadMessageContent } from '../ThreadMessageContentProvider';
import s from './Attachment.module.scss';

type Props = {
  attachment: NonNullable<
    z.infer<typeof threadMessageModel>['attachments']
  >[number];
};

export const Attachment = ({ attachment }: Props) => {
  const { message } = useThreadMessageContent();
  const threadsById = useThreadsStore((store) => store.threadsById);
  const setOpenedFileId = useThreadsStore((store) => store.setOpenedFileId);
  const thread = threadsById[message.thread_id];
  const filesById = thread?.filesById;
  const file = filesById?.[attachment.file_id];
  const isImage = filePathIsImage(file?.filename);
  const type = mime.getType(file?.filename ?? '');

  let Icon = File;
  if (type === 'application/pdf') {
    Icon = FilePdf;
  }

  if (!file) {
    return (
      <div className={s.container}>
        <div className={s.preview}>
          <SvgIcon icon={<Icon />} />
        </div>
        <Placeholder />
      </div>
    );
  }

  return (
    <div
      className={s.container}
      role="button"
      tabIndex={0}
      onClick={() => {
        setOpenedFileId(attachment.file_id);
      }}
    >
      <div className={s.preview}>
        {isImage && typeof file.content === 'string' ? (
          <img src={file.content} alt={file.filename} />
        ) : (
          <SvgIcon icon={<Icon />} />
        )}
      </div>

      <Flex direction="column">
        <Text
          size="text-xs"
          color="sand-12"
          weight={500}
          clampLines={1}
          indicateParentClickable
        >
          {file.filename}
        </Text>
        <Text size="text-2xs" clampLines={1}>
          {formatBytes(file.bytes)}
        </Text>
      </Flex>
    </div>
  );
};
