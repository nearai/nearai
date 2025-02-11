'use client';

import { Card, Flex, Text } from '@near-pagoda/ui';
import { type ReactNode } from 'react';

import { useThreadMessageContent } from '../ThreadMessageContentProvider';

type Props = {
  children: ReactNode;
  messageActions?: ReactNode;
};

export const MessageCard = ({ children, messageActions }: Props) => {
  const { message } = useThreadMessageContent();
  const showFooter = message.role !== 'user' || messageActions;

  return (
    <Card
      animateIn
      background={message.role === 'user' ? 'sand-2' : undefined}
      style={message.role === 'user' ? { alignSelf: 'end' } : undefined}
    >
      {children}

      {showFooter && (
        <Flex align="center" gap="m">
          {message.role !== 'user' && (
            <Text
              size="text-xs"
              style={{
                textTransform: 'capitalize',
              }}
            >
              - {message.role}
            </Text>
          )}

          {messageActions && (
            <Flex align="center" gap="m" style={{ marginLeft: 'auto' }}>
              {messageActions}
            </Flex>
          )}
        </Flex>
      )}
    </Card>
  );
};
