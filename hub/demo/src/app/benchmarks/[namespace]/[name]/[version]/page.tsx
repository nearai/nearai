'use client';

import { Badge, Flex, Section, Text } from '@near-pagoda/ui';

import { useCurrentEntry } from '~/hooks/entries';

export default function EntryDetailsPage() {
  const { currentEntry } = useCurrentEntry('benchmark');

  if (!currentEntry) return null;

  return (
    <>
      <Section>
        <Text size="text-l">Description</Text>

        <Text>{currentEntry.description || 'No description provided.'}</Text>

        {currentEntry.tags.length > 0 && (
          <Flex gap="s" wrap="wrap">
            {currentEntry.tags.map((tag) => (
              <Badge label={tag} variant="neutral" key={tag} />
            ))}
          </Flex>
        )}
      </Section>
    </>
  );
}
