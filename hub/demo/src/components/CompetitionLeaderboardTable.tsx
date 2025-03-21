'use client';

import {
  Badge,
  Flex,
  Grid,
  Input,
  Table,
  Text,
  Tooltip,
  useTable,
} from '@nearai/ui';
import { useMemo, useState } from 'react';

import { useDebouncedValue } from '@/hooks/debounce';
import { DEFAULT_BENCHMARK_COLUMNS } from '@/lib/benchmarks';
import { trpc } from '@/trpc/TRPCProvider';
import { wordsMatchFuzzySearch } from '@/utils/search';

type Props = {
  competitionId: string;
};

export const CompetitionLeaderboardTable = ({ competitionId }: Props) => {
  const [searchQuery, setSearchQuery] = useState('');
  const searchQueryDebounced = useDebouncedValue(searchQuery, 150);
  const evaluationsQuery = trpc.hub.evaluations.useQuery({
    page: competitionId,
  });

  const selectedBenchmarkColumns = useMemo(() => {
    const columns =
      evaluationsQuery.data?.defaultBenchmarkColumns ??
      DEFAULT_BENCHMARK_COLUMNS;

    columns.sort();

    return columns;
  }, [evaluationsQuery.data]);

  const searched = useMemo(() => {
    const evaluations = evaluationsQuery.data?.results;
    if (!evaluations) return evaluations;

    return evaluations.filter((evaluation) => {
      const hasResult = selectedBenchmarkColumns.find((column) => {
        return (
          typeof evaluation[column] !== 'undefined' &&
          evaluation[column] !== null
        );
      });
      if (!hasResult) return false;

      if (!searchQueryDebounced) return true;

      return wordsMatchFuzzySearch(
        [
          ...evaluation.competition_row_tags,
          evaluation.namespace,
          evaluation.provider,
          evaluation.model,
          evaluation.version,
        ],
        searchQueryDebounced,
      );
    });
  }, [evaluationsQuery.data, searchQueryDebounced, selectedBenchmarkColumns]);

  const { sorted, ...tableProps } = useTable({
    data: searched,
    sortColumn: selectedBenchmarkColumns[0]!,
    sortOrder: 'DESCENDING',
  });

  return (
    <>
      <Grid
        columns="1fr 20rem"
        align="center"
        gap="m"
        phone={{ columns: '1fr' }}
      >
        <Flex align="center" gap="m">
          <Text as="h1" size="text-xl">
            Entries
          </Text>
        </Flex>

        <Input
          type="search"
          name="search"
          placeholder="Search Entries"
          value={searchQuery}
          onInput={(event) => setSearchQuery(event.currentTarget.value)}
        />
      </Grid>

      {sorted?.length === 0 ? (
        <>
          {searchQuery ? (
            <Text>No matching results. Try a different search?</Text>
          ) : (
            <Text>No entries submitted yet for this competition.</Text>
          )}
        </>
      ) : (
        <Table.Root {...tableProps}>
          {sorted && (
            <Table.Head>
              <Table.Row>
                <Table.HeadCell
                  column="model"
                  sortable
                  style={{ minWidth: '24rem' }}
                >
                  Model
                </Table.HeadCell>

                <Table.HeadCell style={{ minWidth: '10rem' }}>
                  Entry Status
                </Table.HeadCell>

                {selectedBenchmarkColumns.map((column) => (
                  <Table.HeadCell column={column} sortable key={column}>
                    <Flex
                      as="span"
                      direction="column"
                      style={{ textTransform: 'none' }}
                    >
                      {column.includes('/') && (
                        <Text
                          as="span"
                          size="text-2xs"
                          color="current"
                          noWrap
                          style={{
                            marginBottom: '-0.1rem',
                            display: 'inline-block',
                          }}
                        >
                          {column.split('/').slice(0, -1).join('/')}/
                        </Text>
                      )}
                      <Text
                        as="span"
                        size="text-s"
                        weight={600}
                        color="current"
                        noWrap
                      >
                        {column.split('/').at(-1)}
                      </Text>
                    </Flex>
                  </Table.HeadCell>
                ))}
              </Table.Row>
            </Table.Head>
          )}

          <Table.Body>
            {!sorted && <Table.PlaceholderRows />}

            {sorted?.map((evaluation, index) => (
              <Table.Row key={index}>
                {evaluation.modelId ? (
                  <Table.Cell href={`/models/${evaluation.modelId}`}>
                    <Text size="text-s" weight={600} color="sand-12">
                      {evaluation.modelId}
                    </Text>
                  </Table.Cell>
                ) : (
                  <Table.Cell>
                    <Text size="text-s" color="sand-12">
                      {evaluation.model}
                    </Text>
                  </Table.Cell>
                )}

                <Table.Cell>
                  {evaluation.competition_row_tags.length > 0 ? (
                    <Flex gap="xs">
                      {evaluation.competition_row_tags.includes(
                        'submission',
                      ) && (
                        <Tooltip content="A user's submission to this competition pending review">
                          <Badge
                            label="Submitted"
                            variant="primary"
                            style={{ cursor: 'help' }}
                          />
                        </Tooltip>
                      )}

                      {evaluation.competition_row_tags.includes('baseline') && (
                        <Tooltip content="A baseline model and an example of a submission">
                          <Badge
                            label="Baseline"
                            variant="neutral"
                            style={{ cursor: 'help' }}
                          />
                        </Tooltip>
                      )}

                      {evaluation.competition_row_tags.includes(
                        'reference',
                      ) && (
                        <Tooltip content="Reference metrics for comparison (not a submission)">
                          <Badge
                            label="Reference"
                            variant="neutral"
                            style={{ cursor: 'help' }}
                          />
                        </Tooltip>
                      )}

                      {evaluation.competition_row_tags.includes(
                        'successful_submission',
                      ) && (
                        <Tooltip content="Submission accepted and validated based on competition requirements">
                          <Badge
                            label="Successful"
                            variant="success"
                            style={{ cursor: 'help' }}
                          />
                        </Tooltip>
                      )}

                      {evaluation.competition_row_tags.includes(
                        'disqualified_submission',
                      ) && (
                        <Tooltip content="Submission disqualified for not adhering to competition requirements">
                          <Badge
                            label="Disqualified"
                            variant="alert"
                            style={{ cursor: 'help' }}
                          />
                        </Tooltip>
                      )}
                    </Flex>
                  ) : (
                    <Text size="text-xs" color="sand-8">
                      --
                    </Text>
                  )}
                </Table.Cell>

                {selectedBenchmarkColumns.map((column) => (
                  <Table.Cell key={column}>
                    <Tooltip content={column}>
                      {typeof evaluation[column] === 'number' ? (
                        <Text size="text-s" color="sand-12">
                          {evaluation[column]}%
                        </Text>
                      ) : (
                        <>
                          {evaluation[column] ? (
                            <Text size="text-s">{evaluation[column]}</Text>
                          ) : (
                            <Text size="text-xs" color="sand-8">
                              --
                            </Text>
                          )}
                        </>
                      )}
                    </Tooltip>
                  </Table.Cell>
                ))}
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      )}
    </>
  );
};
