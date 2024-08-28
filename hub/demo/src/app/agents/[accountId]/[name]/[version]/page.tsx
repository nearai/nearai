'use client';

import { useParams } from 'next/navigation';
import { Section } from '~/components/lib/Section';
import { Text } from '~/components/lib/Text';

export default function RegistryItem() {
  const { name } = useParams();

  return (
    <Section>
      <Text as="h1">Agent Details {name}</Text>
    </Section>
  );
}
