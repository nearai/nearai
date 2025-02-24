'use client';

import { Card, Flex, Text } from '@near-pagoda/ui';
import { type ReactNode } from 'react';

import { useThreadMessageContent } from '../ThreadMessageContentProvider';

type Props = {
  actions?: ReactNode;
  children: ReactNode;
};

export const Message = ({ children, actions }: Props) => {
  const { message } = useThreadMessageContent();
  const showFooter = message.role !== 'user' || actions;

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
