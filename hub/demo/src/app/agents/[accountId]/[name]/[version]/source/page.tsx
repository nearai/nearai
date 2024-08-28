'use client';

import { Section } from '~/components/lib/Section';
import { Text } from '~/components/lib/Text';
import { useCurrentResource } from '~/hooks/resources';

export default function AgentSourcePage() {
  const { currentResource, currentVersions } = useCurrentResource('agent');

  if (!currentResource || !currentVersions) return null;

  return (
    <>
      <Section>
        <Text>Viewable source code coming soon!</Text>
      </Section>
    </>
  );
}
