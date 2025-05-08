'use client';

import { Button, Flex, Section, Text } from '@nearai/ui';
import { BookOpenText } from '@phosphor-icons/react';

import { EntriesTable } from '@/components/EntriesTable';

export default function AgentsListPage() {
  return (
    <>
      <Section background="sand-1" padding="standard">
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

      <EntriesTable
        category="agent"
        tags={['featured']}
        defaultSortColumn="updated"
        defaultSortOrder="DESCENDING"
        header={
          <Flex direction="column" gap="xs">
            <Text as="h2" size="text-xl" weight="600">
              Featured Agents
            </Text>
            <Text size="text-s" color="sand-10">
              These agents showcase the capabilities of the NEAR AI platform.
              (Add your agent here by adding the tag 'featured')
            </Text>
          </Flex>
        }
        title="Featured Agents"
      />

      <EntriesTable
        category="agent"
        defaultSortColumn="updated"
        defaultSortOrder="DESCENDING"
        header={
          <Flex direction="column" gap="xs">
            <Text as="h2" size="text-xl" weight="600">
              Agents (Dev)
            </Text>
            <Text size="text-s" color="sand-10">
              All agents in the registry.
            </Text>
          </Flex>
        }
        title="Agents"
      />
    </>
  );
}
