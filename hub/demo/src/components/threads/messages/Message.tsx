'use client';

import { Card, Flex, Text } from '@nearai/ui';
import { type ReactNode } from 'react';

import { useCurrentEntry } from '@/hooks/entries';

import { useThreadMessageContent } from '../ThreadMessageContentProvider';
import { Attachment } from './Attachment';

type Props = {
  actions?: ReactNode;
  children: ReactNode;
};

export const Message = ({ children, actions }: Props) => {
  const { currentEntry } = useCurrentEntry('agent', {
    refetchOnMount: false,
  });
  const { message } = useThreadMessageContent();
  const showFooter = message.role !== 'user' || actions;
  const assistantRoleLabel =
    currentEntry?.details.agent?.assistant_role_label || 'Assistant';
  const showStreamingMessage =
    currentEntry?.details.agent?.show_streaming_message;

  return (
    <Card
      animateIn={!showStreamingMessage || !message.streamed}
      background={message.role === 'user' ? 'sand-2' : undefined}
      style={{
        maxWidth: '100%',
        alignSelf: message.role === 'user' ? 'end' : undefined,
      }}
    >
      {children}

      {message.attachments?.map((attachment) => (
        <Attachment key={attachment.file_id} attachment={attachment} />
      ))}

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
