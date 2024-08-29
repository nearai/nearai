'use client';

import { Play } from '@phosphor-icons/react';

import { Button } from '~/components/lib/Button';
import { Section } from '~/components/lib/Section';
import { Table } from '~/components/lib/Table';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { api } from '~/trpc/react';

export default function AgentsListPage() {
  const list = api.hub.listRegistry.useQuery({ category: 'agent' });

  return (
    <Section>
      <Text as="h1" size="text-2xl">
        Agents{' '}
        {list.data && (
          <Text as="span" size="text-2xl" color="sand10" weight={400}>
            ({list.data.length})
          </Text>
        )}
      </Text>

      <Table.Root>
        <Table.Head>
          <Table.Row>
            <Table.HeadCell>Agent</Table.HeadCell>
            <Table.HeadCell>Creator</Table.HeadCell>
            <Table.HeadCell>Version</Table.HeadCell>
            <Table.HeadCell />
          </Table.Row>
        </Table.Head>

        <Table.Body>
          {!list.data && <Table.PlaceholderRows />}

          {list.data?.map((item, index) => (
            <Table.Row key={index}>
              <Table.Cell
                href={`/agents/${item.namespace}/${item.name}/${item.version}`}
              >
                <Text size="text-s" weight={500} color="violet8">
                  {item.name}
                </Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-s">{item.namespace}</Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-s">{item.version}</Text>
              </Table.Cell>
              <Table.Cell style={{ width: '1px' }}>
                <Tooltip asChild content="Run Agent">
                  <Button
                    label="Run"
                    icon={<Play weight="duotone" />}
                    size="small"
                    fill="outline"
                    href={`/agents/${item.namespace}/${item.name}/${item.version}/run`}
                  />
                </Tooltip>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Section>
  );
}
