'use client';

import { Section } from '~/components/lib/Section';
import { Text } from '~/components/lib/Text';
import { useCurrentResource } from '~/hooks/resources';

export default function AgentSourcePage() {
  const { currentResource } = useCurrentResource('agent');

  if (!currentResource) return null;

  return (
    <>
      <Section>
        <Text weight={500}>Feature coming soon!</Text>
      </Section>
    </>
  );
}
