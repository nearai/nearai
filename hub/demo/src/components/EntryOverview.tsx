'use client';

import { Badge, Flex, Section, Text } from '@nearai/ui';
import { type z } from 'zod';

import { type entryModel } from '@/lib/models';

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
    </>
  );
};
