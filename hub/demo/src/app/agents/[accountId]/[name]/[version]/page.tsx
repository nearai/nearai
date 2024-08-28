'use client';

import { Section } from '~/components/lib/Section';
import { Text } from '~/components/lib/Text';
import { useResourceParams } from '~/hooks/resources';

export default function AgentDetailsPage() {
  const { name } = useResourceParams();

  return (
    <Section>
      <Text as="h1">Agent Details {name}</Text>
    </Section>
  );
}
