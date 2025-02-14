'use client';

import { Flex, SvgIcon, Text } from '@near-pagoda/ui';
import { CheckSquare, ShoppingCart } from '@phosphor-icons/react';
import { type z } from 'zod';

import { useQueryParams } from '~/hooks/url';
import { useThreadsStore } from '~/stores/threads';
import { stringToPotentialJson } from '~/utils/string';

import { Message } from './Message';
import {
  type decisionSchema,
  type requestDecisionSchema,
} from './schema/decision';

type Props = {
  content: z.infer<typeof decisionSchema>['decision'];
};

export const Decision = ({ content }: Props) => {
  const request = useRequestForDecision(content);

  return (
    <Message>
      <Flex direction="column" gap="s" align="start">
        {request?.request_decision.type === 'products' ? (
          <Flex align="center" gap="s">
            <SvgIcon
              icon={<ShoppingCart weight="duotone" />}
              size="xs"
              color="sand-11"
            />
            <Text size="text-xs" weight={600} uppercase>
              Add to cart
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

function useRequestForDecision(content: Props['content']) {
  const { queryParams } = useQueryParams(['threadId']);
  const threadId = queryParams.threadId ?? '';
  const threadsById = useThreadsStore((store) => store.threadsById);
  const thread = threadsById[threadId];
  const messages = thread?.messagesById
    ? Object.values(thread.messagesById)
    : [];
  const allContents = messages.flatMap((m) => m.content);

  let request: z.infer<typeof requestDecisionSchema> | null = null;
  for (const c of allContents) {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-explicit-any
    const json = stringToPotentialJson(c.text?.value ?? '') as any;
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    if (json?.request_decision?.id === content.request_decision_id) {
      request = json as z.infer<typeof requestDecisionSchema>;
      break;
    }
  }

  return request;
}
