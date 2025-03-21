'use client';

import { Flex, SvgIcon, Text } from '@nearai/ui';
import { CheckSquare, ShoppingCart } from '@phosphor-icons/react';
import { type z } from 'zod';

import { useQueryParams } from '@/hooks/url';
import { useThreadMessageContentFilter } from '@/stores/threads';

import { Message } from './Message';
import { type decisionSchema, requestDecisionSchema } from './schema/decisions';

type Props = {
  content: z.infer<typeof decisionSchema>['decision'];
};

export const Decision = ({ content }: Props) => {
  const { queryParams } = useQueryParams(['threadId']);
  const threadId = queryParams.threadId ?? '';

  const requestDecision = useThreadMessageContentFilter(threadId, (json) => {
    if (json?.request_decision) {
      const { data } = requestDecisionSchema.safeParse(json);
      if (data?.request_decision.id === content.request_decision_id) {
        return data;
      }
    }
  })[0];

  return (
    <Message>
      <Flex direction="column" gap="s" align="start">
        {requestDecision?.request_decision.type === 'products' ? (
          <Flex align="center" gap="s">
            <SvgIcon
              icon={<ShoppingCart weight="duotone" />}
              size="xs"
              color="sand-11"
            />
            <Text size="text-xs" weight={600} uppercase>
              Buy Now
            </Text>
          </Flex>
        ) : (
          <Flex align="center" gap="s">
            <SvgIcon
              icon={<CheckSquare weight="duotone" />}
              size="xs"
              color="sand-11"
            />
            <Text size="text-xs" weight={600} uppercase>
              Decision
            </Text>
          </Flex>
        )}

        {content.options.map((option, index) => (
          <Flex align="center" gap="s" key={index}>
            <Text color="sand-12">
              {option.name || option.id}{' '}
              {option.quantity && option.quantity > 1 ? (
                <Text color="sand-12" as="span">
                  (x{option.quantity})
                </Text>
              ) : null}
            </Text>
          </Flex>
        ))}
      </Flex>
    </Message>
  );
};
