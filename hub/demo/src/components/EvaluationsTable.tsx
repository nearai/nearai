'use client';

import {
  BreakpointDisplay,
  Button,
  Card,
  CardList,
  Checkbox,
  CheckboxGroup,
  Dialog,
  Flex,
  Grid,
  Input,
  PlaceholderStack,
  Table,
  Text,
  Tooltip,
  useTable,
} from '@nearai/ui';
import { Eye, Minus, Plus, Table as TableIcon } from '@phosphor-icons/react';
import { type ChangeEventHandler, useMemo, useState } from 'react';
import { type z } from 'zod';

import {
  EntrySelector,
  type EntrySelectorOnSelectHandler,
} from '@/components/EntrySelector';
import { Sidebar } from '@/components/lib/Sidebar';
import { useDebouncedValue } from '@/hooks/debounce';
import { useQueryParams } from '@/hooks/url';
import { DEFAULT_BENCHMARK_COLUMNS } from '@/lib/benchmarks';
import { idForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';
import { trpc } from '@/trpc/TRPCProvider';
import { wordsMatchFuzzySearch } from '@/utils/search';

type Props = {
  benchmarkColumns?: string[];
  entry?: z.infer<typeof entryModel>;
  title?: string;
};

export const EvaluationsTable = ({
  benchmarkColumns: controlledBenchmarkColumns,
  entry: entryToEvaluate,
  title = 'Evaluations',
}: Props) => {
  const { updateQueryPath, queryParams } = useQueryParams([
    'benchmarks',
    'columns',
    'search',
  ]);
  const [benchmarkSelectorIsOpen, setBenchmarkSelectorIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState(queryParams.search ?? '');
  const [sidebarIsOpenForSmallerScreens, setSidebarIsOpenForSmallerScreens] =
    useState(false);
  const searchQueryDebounced = useDebouncedValue(searchQuery, 150);

  const evaluationsQuery = trpc.hub.evaluations.useQuery();
  const benchmarksQuery = trpc.hub.entries.useQuery({
    category: 'benchmark',
  });

  const defaultBenchmarkColumns = useMemo(() => {
    return (
      controlledBenchmarkColumns ??
      evaluationsQuery.data?.defaultBenchmarkColumns ??
      DEFAULT_BENCHMARK_COLUMNS
    );
  }, [controlledBenchmarkColumns, evaluationsQuery.data]);

  const selectedBenchmarkIds = useMemo(() => {
    const ids = queryParams.benchmarks ? queryParams.benchmarks.split(',') : [];

    if (entryToEvaluate?.category === 'benchmark') {
      const id = idForEntry(entryToEvaluate);
      if (!ids.includes(id)) ids.push(idForEntry(entryToEvaluate));
    }

    return [...ids];
  }, [queryParams.benchmarks, entryToEvaluate]);

  const selectedBenchmarkColumns = useMemo(() => {
    const columns = queryParams.columns
      ? queryParams.columns.split(',')
      : selectedBenchmarkIds.length > 0
        ? []
        : defaultBenchmarkColumns;

    columns.sort();

    return columns;
  }, [defaultBenchmarkColumns, queryParams.columns, selectedBenchmarkIds]);

  const selectedBenchmarks = useMemo(() => {
    return benchmarksQuery.data?.filter((entry) =>
      selectedBenchmarkIds.includes(idForEntry(entry)),
    );
  }, [benchmarksQuery.data, selectedBenchmarkIds]);

  const searched = useMemo(() => {
    let evaluations = evaluationsQuery.data?.results;

    if (entryToEvaluate) {
      switch (entryToEvaluate.category) {
        case 'agent':
          evaluations = evaluations?.filter((evaluation) => {
            return (
              evaluation.namespace === entryToEvaluate.namespace &&
              evaluation.agent === entryToEvaluate.name
            );
          });
          break;
        case 'benchmark':
          // Do nothing since this will only impact selected benchmarks in sidebar
          break;
        case 'model':
          evaluations = evaluations?.filter((evaluation) => {
            return (
              evaluation.namespace === entryToEvaluate.namespace &&
              evaluation.model === entryToEvaluate.name
            );
          });
          break;
        default:
          console.warn(
            `Unimplemented entry category for EvaluationsTable: ${entryToEvaluate.category}`,
          );
      }
    }

    if (!evaluations) return evaluations;

    return evaluations.filter((evaluation) => {
      if (!searchQueryDebounced) return true;

      return wordsMatchFuzzySearch(
        [
          evaluation.namespace,
          evaluation.agentId ?? evaluation.agent,
          evaluation.provider,
          evaluation.model,
          evaluation.version,
        ],
        searchQueryDebounced,
      );
    });
  }, [evaluationsQuery.data, searchQueryDebounced, entryToEvaluate]);

  const { sorted, ...tableProps } = useTable({
    data: searched,
    sortColumn: defaultBenchmarkColumns[0]!,
    sortOrder: 'DESCENDING',
  });

  const columnsForBenchmark = (benchmark: z.infer<typeof entryModel>) => {
    if (!evaluationsQuery.data) return [];

    const columns = evaluationsQuery.data.benchmarkColumns.filter(
      (column) =>
        column === benchmark.name || column.startsWith(`${benchmark.name}`),
    );

    if (!columns.length) {
      columns.push(benchmark.name);
    }

    return columns;
  };

  const toggleAllColumnsForBenchmark = (
    benchmark: z.infer<typeof entryModel>,
  ) => {
    let columns = queryParams.columns?.split(',') ?? [];
    const relatedColumns = columnsForBenchmark(benchmark);
    const relatedColumnActiveColumn = columns.find((column) =>
      relatedColumns.includes(column),
    );

    if (relatedColumnActiveColumn) {
      columns = columns.filter((column) => !relatedColumns.includes(column));
    } else {
      columns = [...new Set([...columns, ...relatedColumns])];
    }

    updateQueryPath({ columns: columns.join(',') }, 'replace', false);
  };

  const onFilteredBenchmarkColumnChange: ChangeEventHandler<
    HTMLInputElement
  > = (event) => {
    let columns = [...selectedBenchmarkColumns];

    if (event.target.checked) {
      columns.push(event.target.value);
    } else {
      columns = columns.filter((benchmark) => benchmark !== event.target.value);
    }

    updateQueryPath({ columns: columns.join(',') }, 'replace', false);
  };

  const onSelectBenchmark: EntrySelectorOnSelectHandler = (entry, selected) => {
    let ids = [...selectedBenchmarkIds];
    let columns = queryParams.columns?.split(',') ?? [];
    const relatedColumns = columnsForBenchmark(entry);

    if (selected) {
      ids.push(idForEntry(entry));
      columns = [...new Set([...columns, ...relatedColumns])];
    } else {
      ids = ids.filter((id) => id !== idForEntry(entry));
      columns = columns.filter((column) => !relatedColumns.includes(column));
    }

    updateQueryPath(
      { benchmarks: ids.join(','), columns: columns.join(',') },
      'replace',
      false,
    );
    setBenchmarkSelectorIsOpen(false);
  };

  return (
    <>
      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={sidebarIsOpenForSmallerScreens}
          setOpenForSmallScreens={setSidebarIsOpenForSmallerScreens}
        >
          <Flex align="center" gap="s">
            <Text size="text-xs" weight={600} uppercase>
              Benchmarks
            </Text>

            <Tooltip asChild content="Include a benchmark">
              <Button
                label="Include Benchmark"
                icon={<Plus weight="bold" />}
                variant="affirmative"
                size="x-small"
                fill="ghost"
                onClick={() => setBenchmarkSelectorIsOpen(true)}
              />
            </Tooltip>
          </Flex>

          <Text size="text-s">
            Include benchmarks to view specific evaluation metrics (columns).
          </Text>

          {selectedBenchmarks ? (
            <Sidebar.SidebarContentBleed>
              <CardList>
                {selectedBenchmarks.map((benchmark) => (
                  <Card padding="m" background="sand-2" key={benchmark.id}>
                    <Flex gap="xs">
                      <Flex direction="column" style={{ marginRight: 'auto' }}>
                        <Text size="text-s" weight={500} color="sand-12">
                          {benchmark.name} {benchmark.version}
                        </Text>
                        <Text
                          size="text-xs"
                          color="sand-11"
                          href={`/profiles/${benchmark.namespace}`}
                          decoration="none"
                        >
                          @{benchmark.namespace}
                        </Text>
                      </Flex>

                      <Tooltip asChild content="Toggle all columns">
                        <Button
                          label="Toggle all columns"
                          icon={<Eye weight="duotone" />}
                          size="x-small"
                          fill="ghost"
                          onClick={() =>
                            toggleAllColumnsForBenchmark(benchmark)
                          }
                        />
                      </Tooltip>

                      <Tooltip asChild content="Remove benchmark">
                        <Button
                          label="Remove benchmark"
                          icon={<Minus />}
                          size="x-small"
                          fill="ghost"
                          onClick={() => onSelectBenchmark(benchmark, false)}
                        />
                      </Tooltip>
                    </Flex>

                    <CheckboxGroup aria-label="Include Evaluation Columns">
                      {columnsForBenchmark(benchmark).map((column) => (
                        <Flex as="label" align="center" gap="s" key={column}>
                          <Checkbox
                            name={`columns-${column}`}
                            value={column}
                            checked={selectedBenchmarkColumns.includes(column)}
                            onChange={onFilteredBenchmarkColumnChange}
                          />
                          <Text as="span" size="text-s" color="sand-12">
                            {column.replace(`${benchmark.name}/`, '')}
                          </Text>
                        </Flex>
                      ))}
                    </CheckboxGroup>
                  </Card>
                ))}
              </CardList>
            </Sidebar.SidebarContentBleed>
          ) : (
            <PlaceholderStack />
          )}
        </Sidebar.Sidebar>

        <Sidebar.Main>
          <Grid
            columns="1fr 20rem"
            align="center"
            gap="m"
            phone={{ columns: '1fr' }}
          >
            <Flex align="center" gap="m">
              <Text as="h1" size="text-2xl">
                {title}
              </Text>

              <BreakpointDisplay show="sidebar-small-screen">
                <Button
                  label="Edit Benchmarks"
                  icon={<TableIcon />}
                  size="small"
                  fill="outline"
                  onClick={() => setSidebarIsOpenForSmallerScreens(true)}
                />
              </BreakpointDisplay>
            </Flex>

            <Input
              type="search"
              name="search"
              placeholder="Search Evaluations"
              value={searchQuery}
              onInput={(event) => setSearchQuery(event.currentTarget.value)}
            />
          </Grid>

          {sorted?.length === 0 ? (
            <>
              {searchQuery ? (
                <Text>No matching results. Try a different search?</Text>
              ) : (
                <Text>
                  {entryToEvaluate
                    ? `No evaluations exist yet for this ${entryToEvaluate.category}.`
                    : 'No evaluations exist yet.'}
                </Text>
              )}
            </>
          ) : (
            <Table.Root {...tableProps}>
              {sorted && (
                <Table.Head>
                  <Table.Row>
                    <Table.HeadCell column="provider" sortable>
                      Provider
                    </Table.HeadCell>

                    <Table.HeadCell
                      column="model"
                      sortable
                      style={{ minWidth: '12rem' }}
                    >
                      Model
                    </Table.HeadCell>

                    <Table.HeadCell
                      column="agentId"
                      sortable
                      style={{ minWidth: '15rem' }}
                    >
                      Agent
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
                    <Table.Cell>
                      <Text size="text-s">{evaluation.provider}</Text>
                    </Table.Cell>

                    <Table.Cell>
                      <Text size="text-s">{evaluation.model}</Text>
                    </Table.Cell>

                    {evaluation.agentId ? (
                      <Table.Cell href={`/agents/${evaluation.agentId}`}>
                        <Text size="text-s" weight={500} color="sand-12">
                          {evaluation.agentId}
                        </Text>
                      </Table.Cell>
                    ) : (
                      <Table.Cell>
                        <Text size="text-xs" color="sand-8">
                          --
                        </Text>
                      </Table.Cell>
                    )}

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
        </Sidebar.Main>
      </Sidebar.Root>

      <Dialog.Root
        open={benchmarkSelectorIsOpen}
        onOpenChange={setBenchmarkSelectorIsOpen}
      >
        <Dialog.Content title="Benchmarks" align="stretch">
          <EntrySelector
            category="benchmark"
            description="Select benchmarks to include in the evaluations table."
            selectedIds={selectedBenchmarkIds}
            onSelect={onSelectBenchmark}
          />
        </Dialog.Content>
      </Dialog.Root>
    </>
  );
};
