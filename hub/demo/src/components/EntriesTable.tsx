'use client';

import {
  Badge,
  Button,
  Flex,
  Grid,
  Input,
  Section,
  Table,
  Text,
  Tooltip,
  useTable,
} from '@nearai/ui';
import { ChatCircleDots, CodeBlock, Play } from '@phosphor-icons/react';
import { format, formatDistanceToNow } from 'date-fns';
import { type ReactNode } from 'react';

import { env } from '@/env';
import { useEntriesSearch } from '@/hooks/entries';
import { useClientPagination } from '@/hooks/pagination';
import { ENTRY_CATEGORY_LABELS } from '@/lib/categories';
import {
  benchmarkEvaluationsUrlForEntry,
  primaryUrlForEntry,
  sourceUrlForEntry,
} from '@/lib/entries';
import { type EntryCategory } from '@/lib/models';
import { trpc } from '@/trpc/TRPCProvider';

import { ForkButton } from './ForkButton';
import { NewAgentButton } from './NewAgentButton';
import { Pagination } from './Pagination';
import { StarButton } from './StarButton';

type Props = {
  bleed?: boolean;
  category: EntryCategory;
  header?: ReactNode;
  forkOf?: {
    name: string;
    namespace: string;
  };
  title: string;
};

export const EntriesTable = ({
  bleed,
  category,
  forkOf,
  header,
  title,
}: Props) => {
  const entriesQuery = trpc.hub.entries.useQuery({ category, forkOf });

  const { searched, searchQuery, setSearchQuery } = useEntriesSearch(
    entriesQuery.data,
  );

  const { sorted, ...tableProps } = useTable({
    data: searched,
    sortColumn: 'num_stars',
    sortOrder: 'DESCENDING',
  });

  const { pageItems, totalPages, setPage, ...paginationProps } =
    useClientPagination({
      data: sorted,
      itemsPerPage: 30,
    });

  return (
    <Section bleed={bleed} padding={bleed ? 'none' : undefined}>
      <Grid
        columns="1fr 20rem"
        align="center"
        gap="m"
        tablet={{ columns: '1fr', align: 'end' }}
      >
        {header || (
          <Flex align="center" gap="m" wrap="wrap">
            <Text as="h1" size="text-2xl" style={{ marginRight: 'auto' }}>
              {title}{' '}
              {entriesQuery.data && (
                <Text as="span" size="text-2xl" color="sand-10" weight={400}>
                  ({entriesQuery.data.length})
                </Text>
              )}
            </Text>

            {category === 'agent' && <NewAgentButton />}
          </Flex>
        )}

        <Input
          type="search"
          name="search"
          placeholder={`Search ${title}`}
          onInput={(event) => {
            setPage(undefined);
            setSearchQuery(event.currentTarget.value);
          }}
        />
      </Grid>

      {sorted?.length === 0 ? (
        <>
          {searchQuery && (
            <Text>No matches found. Try a different search?</Text>
          )}
          {!searchQuery && entriesQuery.data?.length === 0 && (
            <Text>No {title.toLowerCase()} exist yet.</Text>
          )}
        </>
      ) : (
        <Table.Root
          {...tableProps}
          setSort={(value) => {
            void entriesQuery.refetch();
            setPage(undefined);
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
              <Table.HeadCell column="updated" sortable>
                Updated
              </Table.HeadCell>
              <Table.HeadCell>Tags</Table.HeadCell>
              <Table.HeadCell
                column="num_stars"
                sortable
                style={{ paddingLeft: '1rem' }}
              >
                Stars
              </Table.HeadCell>
              <Table.HeadCell
                column="num_forks"
                sortable
                style={{ paddingLeft: '1rem' }}
              >
                Forks
              </Table.HeadCell>
              <Table.HeadCell />
            </Table.Row>
          </Table.Head>

          <Table.Body>
            {!sorted && <Table.PlaceholderRows />}

            {pageItems?.map((entry) => (
              <Table.Row key={entry.id}>
                <Table.Cell
                  href={primaryUrlForEntry(entry)}
                  style={{ minWidth: '10rem', maxWidth: '20rem' }}
                >
                  <Flex direction="column">
                    <Text size="text-s" weight={600} color="sand-12">
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
                  <Text size="text-s" color="sand-12" clampLines={1}>
                    {entry.namespace}
                  </Text>
                </Table.Cell>

                <Table.Cell>
                  <Text size="text-s">{entry.version}</Text>
                </Table.Cell>

                <Table.Cell>
                  <Text size="text-xs">
                    <Tooltip content={format(entry.updated, 'PPpp')}>
                      <span>
                        {formatDistanceToNow(entry.updated, {
                          addSuffix: true,
                        })}
                      </span>
                    </Tooltip>
                  </Text>
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
                  <ForkButton entry={entry} variant="simple" />
                </Table.Cell>

                <Table.Cell style={{ width: '1px' }}>
                  <Flex align="center" gap="xs">
                    {!env.NEXT_PUBLIC_CONSUMER_MODE && (
                      <>
                        {benchmarkEvaluationsUrlForEntry(entry) && (
                          <Tooltip asChild content="View evaluations">
                            <Button
                              label="View evaluations"
                              icon={ENTRY_CATEGORY_LABELS.evaluation.icon}
                              size="small"
                              fill="ghost"
                              href={benchmarkEvaluationsUrlForEntry(entry)}
                            />
                          </Tooltip>
                        )}

                        {sourceUrlForEntry(entry) && (
                          <Tooltip asChild content="View source">
                            <Button
                              label="View source"
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
                            ? 'Chat with agent'
                            : 'Run agent'
                        }
                      >
                        <Button
                          label="Run agent"
                          icon={
                            env.NEXT_PUBLIC_CONSUMER_MODE ? (
                              <ChatCircleDots weight="duotone" />
                            ) : (
                              <Play weight="duotone" />
                            )
                          }
                          size="small"
                          fill="ghost"
                          href={`${primaryUrlForEntry(entry)}/run`}
                        />
                      </Tooltip>
                    )}
                  </Flex>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>

          {totalPages > 1 && (
            <Table.Foot sticky={false}>
              <Table.Row>
                <Table.Cell colSpan={100}>
                  <Pagination {...paginationProps} />
                </Table.Cell>
              </Table.Row>
            </Table.Foot>
          )}
        </Table.Root>
      )}
    </Section>
  );
};
