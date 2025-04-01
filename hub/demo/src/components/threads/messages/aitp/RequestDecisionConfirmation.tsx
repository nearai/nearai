'use client';

import { Button, Flex, Text } from '@nearai/ui';
import { type z } from 'zod';

import { useThreadsStore } from '@/stores/threads';

import { Message } from './Message';
import {
  CURRENT_AITP_DECISIONS_SCHEMA_URL,
  type decisionSchema,
  type requestDecisionSchema,
} from './schema/decisions';

type Props = {
  content: z.infer<typeof requestDecisionSchema>['request_decision'];
};

const defaultOptions: Props['content']['options'] = [
  {
    id: 'yes',
    name: 'Yes',
  },
  {
    id: 'no',
    name: 'No',
  },
];

export const RequestDecisionConfirmation = ({ content }: Props) => {
  const addMessage = useThreadsStore((store) => store.addMessage);
  const options = content.options?.length ? content.options : defaultOptions;

  if (content.type !== 'confirmation') {
    console.error(
      `Attempted to render <RequestDecisionConfirmation /> with invalid content type: ${content.type}`,
    );
    return null;
  }

  const submitDecision = async (
    option: Props['content']['options'][number],
  ) => {
    if (!addMessage) return;

    const result: z.infer<typeof decisionSchema> = {
      $schema: CURRENT_AITP_DECISIONS_SCHEMA_URL,
      decision: {
        request_decision_id: content.id,
        options: [
          {
            id: option.id,
            name: option.name,
          },
        ],
      },
    };

    void addMessage({
      new_message: JSON.stringify(result),
    });
  };

  return (
    <Message>
      {(content.title || content.description) && (
        <Flex direction="column" gap="s">
          {content.title && (
            <Text size="text-xs" weight={600} uppercase>
              {content.title}
            </Text>
          )}
          {content.description && (
            <Text color="sand-12">{content.description}</Text>
          )}
        </Flex>
      )}

      <Flex align="center" gap="s" wrap="wrap">
        {options.map((option, index) => (
          <Button
            label={option.name || option.id}
            variant="affirmative"
            key={option.id + index}
            onClick={() => submitDecision(option)}
          />
        ))}
      </Flex>
    </Message>
  );
};
