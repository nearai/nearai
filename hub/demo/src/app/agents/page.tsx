'use client';

import { Section } from '~/components/lib/Section';
import { Table } from '~/components/lib/Table';
import { Text } from '~/components/lib/Text';
import { api } from '~/trpc/react';

export default function Agents() {
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
            <Table.HeadCell></Table.HeadCell>
          </Table.Row>
        </Table.Head>

        <Table.Body>
          {!list.data && <Table.PlaceholderRows />}

          {list.data?.map((item, index) => (
            <Table.Row key={index}>
              <Table.Cell>
                <Text size="text-s">{item.name}</Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-s">{item.namespace}</Text>
              </Table.Cell>
              <Table.Cell>
                <Text size="text-s">{item.version}</Text>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Section>
  );
}
