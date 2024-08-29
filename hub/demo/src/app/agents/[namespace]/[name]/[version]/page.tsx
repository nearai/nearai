'use client';

import { Badge } from '~/components/lib/Badge';
import { Flex } from '~/components/lib/Flex';
import { Section } from '~/components/lib/Section';
import { Text } from '~/components/lib/Text';
import { useCurrentResource } from '~/hooks/resources';

export default function AgentDetailsPage() {
  const { currentResource } = useCurrentResource('agent');

  if (!currentResource) return null;

  return (
    <>
      <Section>
        <Text>{currentResource.description}</Text>

        <Flex gap="s" wrap="wrap">
          {currentResource.tags.map((tag) => (
            <Badge label={tag} variant="neutral" key={tag} />
          ))}
        </Flex>
      </Section>
    </>
  );
}
