'use client';

import { Card, Flex, Text } from '@near-pagoda/ui';
import { type ReactNode } from 'react';

import { useCurrentEntry } from '~/hooks/entries';

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
