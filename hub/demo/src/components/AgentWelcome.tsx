'use client';

import { Container, Flex, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import { type entryModel } from '~/lib/models';

type Props = {
  details: z.infer<typeof entryModel>['details'];
};

export const AgentWelcome = ({ details }: Props) => {
  const welcome = details.agent?.welcome;

  if (!welcome?.title || !welcome?.description) return null;

  return (
    <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
      <Flex direction="column" gap="m" align="center">
        <Text size="text-l">{welcome.title}</Text>
        <Text>{welcome.description}</Text>
      </Flex>
    </Container>
  );
};
