'use client';

import { ChatCircleDots, CodeBlock, Play } from '@phosphor-icons/react';

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
import { env } from '~/env';
import { useEntriesSearch } from '~/hooks/entries';
import {
  benchmarkEvaluationsUrlForEntry,
  ENTRY_CATEGORY_LABELS,
  primaryUrlForEntry,
  sourceUrlForEntry,
} from '~/lib/entries';
import { type EntryCategory } from '~/lib/models';
import { api } from '~/trpc/react';

import { StarButton } from './StarButton';

type Props = {
  category: EntryCategory;
  title: string;
};

export const EntriesTable = ({ category, title }: Props) => {
  const entriesQuery = api.hub.entries.useQuery({ category });

  const { searched, searchQuery, setSearchQuery } = useEntriesSearch(
    entriesQuery.data,
  );

  const { sorted, ...tableProps } = useTable({
    data: searched,
    sortColumn: 'num_stars',
    sortOrder: 'DESCENDING',
  });

  return (
    <Section>
      <Grid
        columns="1fr 20rem"
        align="center"
        gap="m"
        phone={{ columns: '1fr' }}
      >
        <Text as="h1" size="text-2xl">
          {title}{' '}
          {entriesQuery.data && (
            <Text as="span" size="text-2xl" color="sand-10" weight={400}>
              ({entriesQuery.data.length})
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

      <Table.Root
        {...tableProps}
        setSort={(value) => {
          void entriesQuery.refetch();
          tableProps.setSort(value);
        }}
      >
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
            <Table.HeadCell
              column="num_stars"
              style={{ paddingLeft: '1.4rem' }}
            >
              Stars
            </Table.HeadCell>
            <Table.HeadCell />
          </Table.Row>
        </Table.Head>

        <Table.Body>
          {!sorted && <Table.PlaceholderRows />}

          {sorted?.map((entry, index) => (
            <Table.Row key={index}>
              <Table.Cell
                href={primaryUrlForEntry(entry)}
                style={{ minWidth: '10rem', maxWidth: '20rem' }}
              >
                <Flex direction="column">
                  <Text
                    size="text-s"
                    weight={500}
                    color="sand-12"
                    clickableHighlight
                  >
                    {entry.name}
                  </Text>
                  <Text size="text-xs" clampLines={1}>
                    {entry.description}
                  </Text>
                </Flex>
              </Table.Cell>

              <Table.Cell
                href={`/profiles/${entry.namespace}`}
                style={{ minWidth: '8rem', maxWidth: '12rem' }}
              >
                <Text size="text-s" weight={500} clampLines={1}>
                  {entry.namespace}
                </Text>
              </Table.Cell>

              <Table.Cell>
                <Text size="text-s">{entry.version}</Text>
              </Table.Cell>

              <Table.Cell style={{ maxWidth: '14rem', overflow: 'hidden' }}>
                <Flex gap="xs">
                  {entry.tags.map((tag) => (
                    <Badge label={tag} variant="neutral" key={tag} />
                  ))}
                </Flex>
              </Table.Cell>

              <Table.Cell style={{ width: '1px' }}>
                <StarButton entry={entry} variant="simple" />
              </Table.Cell>

              <Table.Cell style={{ width: '1px' }}>
                <Flex align="center" gap="xs">
                  {!env.NEXT_PUBLIC_CONSUMER_MODE && (
                    <>
                      {benchmarkEvaluationsUrlForEntry(entry) && (
                        <Tooltip asChild content="View Evaluations">
                          <Button
                            label="View Evaluations"
                            icon={ENTRY_CATEGORY_LABELS.evaluation.icon}
                            size="small"
                            fill="ghost"
                            href={benchmarkEvaluationsUrlForEntry(entry)}
                          />
                        </Tooltip>
                      )}

                      {sourceUrlForEntry(entry) && (
                        <Tooltip asChild content="View Source">
                          <Button
                            label="View Source"
                            icon={<CodeBlock weight="duotone" />}
                            size="small"
                            fill="ghost"
                            href={sourceUrlForEntry(entry)}
                          />
                        </Tooltip>
                      )}
                    </>
                  )}

                  {category === 'agent' && (
                    <Tooltip
                      asChild
                      content={
                        env.NEXT_PUBLIC_CONSUMER_MODE
                          ? 'Chat With Agent'
                          : 'Run Agent'
                      }
                    >
                      <Button
                        label="Run Agent"
                        icon={
                          env.NEXT_PUBLIC_CONSUMER_MODE ? (
                            <ChatCircleDots weight="duotone" />
                          ) : (
                            <Play weight="duotone" />
                          )
                        }
                        size="small"
                        fill="ghost"
                        href={`/agents/${entry.namespace}/${entry.name}/${entry.version}/run`}
                      />
                    </Tooltip>
                  )}
                </Flex>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Section>
  );
};
