'use client';

import { Button, Card, Flex, HR, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import { type requestChoiceSchema } from './schema';

type Props = {
  id: string;
  content: z.infer<typeof requestChoiceSchema>['request_choice'];
};

const defaultOptions: Props['content']['options'] = [
  {
    name: 'Yes',
  },
  {
    name: 'No',
  },
];

export const RequestChoiceConfirmation = ({ content }: Props) => {
  const options = content.options?.length ? content.options : defaultOptions;

  return (
    <Card animateIn>
      {(content.title || content.description) && (
        <>
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
        </>
      )}

      <Flex align="center" gap="s" wrap="wrap">
        {options.map((option, index) => (
          <Button
            label={option.name}
            variant={index === 0 ? 'affirmative' : 'secondary'}
            key={option.name + index}
          />
        ))}
      </Flex>
    </Card>
  );
};
