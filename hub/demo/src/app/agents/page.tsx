'use client';

import { Button, Flex, Section, Text } from '@nearai/ui';
import { BookOpenText } from '@phosphor-icons/react';

import { EntriesTable } from '@/components/EntriesTable';

export default function AgentsListPage() {
  return (
    <>
      <Section background="sand-1" padding="l">
        <Flex direction="column" gap="m">
          <Text as="h2" size="text-xl" weight="600">
            Agent Examples
          </Text>
          <Text>
            Find examples and documentation to help you get started building
            agents.
          </Text>
          <Button
            label="View Examples & FAQ"
            icon={<BookOpenText weight="duotone" />}
            href="https://github.com/nearai/nearai/issues/1080"
            target="_blank"
            style={{ alignSelf: 'flex-start' }}
          />
        </Flex>
      </Section>

      <Section background="sand-2" padding="l">
        <Flex direction="column" gap="m">
          <Text as="h2" size="text-xl" weight="600">
            Featured Agents
          </Text>
          <Text>
            These agents showcase the capabilities of the NEAR AI platform.
            <br />
            <Text as="span" size="text-s" color="sand-10">
              (Add your agent here by adding the tag &apos;featured&apos;)
            </Text>
          </Text>
        </Flex>
      </Section>

      <EntriesTable
        category="agent"
        title="Featured Agents"
        tags={['featured']}
        defaultSortColumn="updated"
        defaultSortOrder="DESCENDING"
        bleed
      />

      <Section background="sand-1" padding="l">
        <Flex direction="column" gap="m">
          <Text as="h2" size="text-xl" weight="600">
            Agents (Dev)
          </Text>
          <Text>All agents in the registry.</Text>
        </Flex>
      </Section>

      <EntriesTable
        category="agent"
        title="Agents"
        defaultSortColumn="updated"
        defaultSortOrder="DESCENDING"
        bleed
      />
    </>
  );
}
