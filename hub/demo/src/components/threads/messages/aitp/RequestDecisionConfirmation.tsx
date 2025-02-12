'use client';

import { Button, Card, Flex, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import { type requestDecisionSchema } from './schema/decision';

type Props = {
  contentId: string;
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
    // TODO
    console.log('Selected option:', option);
  };

  return (
    <Card animateIn>
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
            variant={index === 0 ? 'affirmative' : 'secondary'}
            key={option.id + index}
            onClick={() => submitDecision(option)}
          />
        ))}
      </Flex>
    </Card>
  );
};
