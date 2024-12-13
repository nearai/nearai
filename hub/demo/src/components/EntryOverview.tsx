'use client';

import { Badge, Flex, Grid, Section, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import { type entryModel } from '~/lib/models';

import { ForkButton } from './ForkButton';
import { Markdown } from './lib/Markdown';

type Props = {
  entry: z.infer<typeof entryModel>;
};

export const EntryOverview = ({ entry }: Props) => {
  return (
    <Grid
      columns="1fr 1fr"
      align="stretch"
      style={{ flexGrow: 1 }}
      tablet={{ columns: '1fr' }}
    >
      <Section background="sand-2" gap="m" bleed>
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

      <Section background="sand-1" gap="m" bleed>
        <Flex align="center" gap="s">
          <Text size="text-l">Forks</Text>
          <ForkButton entry={entry} variant="simple" />
        </Flex>

        <Text color="sand-10" size="text-s">
          This {entry.category} {`hasn't`} been forked yet.
        </Text>

        {/* TODO: Create endpoint for fetching all forks of entry */}
        {/* TODO: Update all other overview pages for models, datasets, etc */}
        {/* <EntryCard entry={currentEntry} /> */}
      </Section>
    </Grid>
  );
};
