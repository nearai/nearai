'use client';

import { Badge, Card, Flex, Text } from '@nearai/ui';
import { Paperclip } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { useCurrentEntry } from '@/hooks/entries';
import { useThreadsStore } from '@/stores/threads';

import { useThreadMessageContent } from '../ThreadMessageContentProvider';

type Props = {
  actions?: ReactNode;
  children: ReactNode;
};

export const Message = ({ children, actions }: Props) => {
  const { currentEntry } = useCurrentEntry('agent', {
    refetchOnMount: false,
  });
  const { message } = useThreadMessageContent();
  const threadsById = useThreadsStore((store) => store.threadsById);
  const setOpenedFileId = useThreadsStore((store) => store.setOpenedFileId);
  const thread = threadsById[message.thread_id];
  const filesById = thread?.filesById;
  const showFooter = message.role !== 'user' || actions;
  const assistantRoleLabel =
    currentEntry?.details.agent?.assistant_role_label || 'Assistant';

  return (
    <Card
      animateIn
      background={message.role === 'user' ? 'sand-2' : undefined}
      style={{
        maxWidth: '100%',
        alignSelf: message.role === 'user' ? 'end' : undefined,
      }}
    >
      {children}

      {filesById && !!message.attachments?.length && (
        <Flex gap="s" wrap="wrap">
          {message.attachments?.map((attachment) => (
            <Badge
              key={attachment.file_id}
              label={filesById[attachment.file_id]?.filename}
              iconLeft={<Paperclip />}
              onClick={() => {
                setOpenedFileId(attachment.file_id);
              }}
            />
          ))}
        </Flex>
      )}

      {showFooter && (
        <Flex align="center" gap="m">
          {message.role !== 'user' && (
            <Text size="text-xs">
              - {message.role === 'assistant' ? assistantRoleLabel : 'System'}
            </Text>
          )}

          {actions && (
            <Flex align="center" gap="m" style={{ marginLeft: 'auto' }}>
              {actions}
            </Flex>
          )}
        </Flex>
      )}
    </Card>
  );
};
