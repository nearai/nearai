'use client';

import { Container, Flex, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import { type entryModel } from '~/lib/models';

import { Markdown } from './lib/Markdown';

type Props = {
  details: z.infer<typeof entryModel>['details'];
};

export const AgentWelcome = ({ details }: Props) => {
  const welcome = details.agent?.welcome;

  if (!welcome?.title || !welcome?.description) return null;

  return (
    <Container size="s" style={{ margin: 'auto' }}>
      <Flex
        direction="column"
        gap="m"
        style={{
          borderImageSource:
            'linear-gradient(to bottom, var(--green-9), var(--violet-9))',
          borderImageSlice: 1,
          borderLeft: '2px solid',
          paddingLeft: 'var(--gap-l)',
        }}
      >
        {welcome.title && <Text size="text-l">{welcome.title}</Text>}
        <Markdown content={`How can I help you today?`} />
      </Flex>
    </Container>
  );
};
