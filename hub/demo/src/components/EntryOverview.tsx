'use client';

import { Badge, Flex, Section, Text } from '@nearai/ui';
import { type z } from 'zod';

import { type entryModel } from '@/lib/models';

import { EntriesTable } from './EntriesTable';
import { ForkButton } from './ForkButton';
import { Markdown } from './lib/Markdown';

type Props = {
  entry: z.infer<typeof entryModel>;
};

export const EntryOverview = ({ entry }: Props) => {
  return (
    <>
      <Section background="sand-2">
        <Text size="text-l">Description</Text>

        <Markdown
          content={
            entry.description ||
            `No description provided for this ${entry.category}.`
          }
        />

        {entry.tags.length > 0 && (
          <Flex gap="s" wrap="wrap">
            {entry.tags.map((tag) => (
              <Badge label={tag} variant="neutral" key={tag} />
            ))}
          </Flex>
        )}
      </Section>

      <EntriesTable
        category={entry.category}
        header={
          <Flex align="center" gap="s">
            <Text size="text-l">Forks</Text>
            <ForkButton entry={entry} variant="simple" />
          </Flex>
        }
        forkOf={{
          name: entry.name,
          namespace: entry.namespace,
        }}
        title="Forks"
      />
    </>
  );
};
