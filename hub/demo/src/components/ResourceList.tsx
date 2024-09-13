'use client';

import { CodeBlock, Play } from '@phosphor-icons/react';
import Head from 'next/head';

import { Badge } from '~/components/lib/Badge';
import { Button } from '~/components/lib/Button';
import { Flex } from '~/components/lib/Flex';
import { Grid } from '~/components/lib/Grid';
import { Input } from '~/components/lib/Input';
import { Section } from '~/components/lib/Section';
import { Table } from '~/components/lib/Table';
import { useTable } from '~/components/lib/Table/hooks';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { useResourceSearch } from '~/hooks/resources';
import { type RegistryCategory } from '~/server/api/routers/hub';
import { api } from '~/trpc/react';

type Props = {
  category: RegistryCategory;
  title: string;
};

export const ResourceList = ({ category, title }: Props) => {
  const listQuery = api.hub.registryEntries.useQuery({ category });

  const { searched, searchQuery, setSearchQuery } = useResourceSearch(
    listQuery.data,
  );

  const { sorted, ...tableProps } = useTable({
    data: searched,
    sortColumn: 'name',
  });

  return (
    <Section>
      <Head>
        <title>{title}</title>
      </Head>

      <Grid
        columns="1fr 20rem"
        align="center"
        gap="m"
        phone={{ columns: '1fr' }}
      >
        <Text as="h1" size="text-2xl">
          {title}{' '}
          {listQuery.data && (
            <Text as="span" size="text-2xl" color="sand-10" weight={400}>
              ({listQuery.data.length})
            </Text>
          )}
        </Text>

        <Input
          type="search"
          name="search"
          placeholder={`Search ${title}`}
          value={searchQuery}
          onInput={(event) => setSearchQuery(event.currentTarget.value)}
        />
      </Grid>

      <Table.Root {...tableProps}>
        <Table.Head>
          <Table.Row>
            <Table.HeadCell column="name" sortable>
              Name
            </Table.HeadCell>
            <Table.HeadCell column="namespace" sortable>
              Creator
            </Table.HeadCell>
            <Table.HeadCell>Version</Table.HeadCell>
            <Table.HeadCell>Tags</Table.HeadCell>
            {category === 'agent' && <Table.HeadCell />}
          </Table.Row>
        </Table.Head>

        <Table.Body>
          {!listQuery.data && <Table.PlaceholderRows />}

          {sorted.map((item, index) => (
            <Table.Row key={index}>
              {category === 'agent' ? (
                <Table.Cell
                  href={`/agents/${item.namespace}/${item.name}/${item.version}`}
                  style={{ width: '20rem' }}
                >
                  <Text size="text-s" weight={500} color="violet-11">
                    {item.name}
                  </Text>
                </Table.Cell>
              ) : (
                <Table.Cell style={{ width: '20rem' }}>
                  <Text size="text-s" weight={500} color="sand-12">
                    {item.name}
                  </Text>
                </Table.Cell>
              )}

              <Table.Cell>
                <Text size="text-s">{item.namespace}</Text>
              </Table.Cell>

              <Table.Cell>
                <Text size="text-s">{item.version}</Text>
              </Table.Cell>

              <Table.Cell>
                <Flex wrap="wrap" gap="xs" style={{ width: '15rem' }}>
                  {item.tags.map((tag) => (
                    <Badge label={tag} variant="neutral" key={tag} />
                  ))}
                </Flex>
              </Table.Cell>

              {category === 'agent' && (
                <Table.Cell style={{ width: '1px' }}>
                  <Flex align="center" gap="xs">
                    <Tooltip asChild content="View Source">
                      <Button
                        label="View Source"
                        icon={<CodeBlock weight="duotone" />}
                        size="small"
                        fill="ghost"
                        href={`/agents/${item.namespace}/${item.name}/${item.version}/source`}
                      />
                    </Tooltip>

                    <Tooltip asChild content="Run Agent">
                      <Button
                        label="Run"
                        icon={<Play weight="duotone" />}
                        size="small"
                        fill="ghost"
                        href={`/agents/${item.namespace}/${item.name}/${item.version}/run`}
                      />
                    </Tooltip>
                  </Flex>
                </Table.Cell>
              )}
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Section>
  );
};
