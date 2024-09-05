'use client';

import { type z } from 'zod';

import { type registryEntry } from '~/lib/models';

import { Container } from './lib/Container';
import { Flex } from './lib/Flex';
import { ImageIcon } from './lib/ImageIcon';
import { Text } from './lib/Text';

type Props = {
  details: z.infer<typeof registryEntry>['details'];
};

export const AgentWelcome = ({ details }: Props) => {
  const welcome = details.agent?.welcome;

  if (!welcome?.title || !welcome?.description) return null;

  return (
    <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
      <Flex direction="column" gap="m" align="center">
        {details?.icon && (
          <ImageIcon src={details.icon} alt={welcome.title} size="l" />
        )}
        <Text size="text-l">{welcome.title}</Text>
        <Text>{welcome.description}</Text>
      </Flex>
    </Container>
  );
};
