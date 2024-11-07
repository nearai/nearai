'use client';

import { Badge, Flex, Section } from '@near-pagoda/ui';

import { Markdown } from '~/components/lib/Markdown';
import { useCurrentEntry } from '~/hooks/entries';

export default function EntryDetailsPage() {
  const { currentEntry } = useCurrentEntry('agent');

  if (!currentEntry) return null;

  return (
    <>
      <Section>
        <Markdown
          content={currentEntry.description || 'No description provided.'}
        />

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
