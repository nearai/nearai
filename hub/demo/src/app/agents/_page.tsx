/*
  NOTE: This page is temporarily disabled since it's not fully functional at the moment. 
  It provides UI pattern examples for filtering with a sidebar and adding more columns.
*/

'use client';

import { GitFork, Play, SlidersHorizontal } from '@phosphor-icons/react';
import { useState } from 'react';

import { Badge } from '~/components/lib/Badge';
import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Checkbox } from '~/components/lib/Checkbox';
import { Flex } from '~/components/lib/Flex';
import { Sidebar } from '~/components/lib/Sidebar';
import { Table } from '~/components/lib/Table';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { api } from '~/trpc/react';

const filters = [
  'DeFi',
  'Business Process',
  'Customer Service',
  'Legal',
  'Medical / Health',
];

export default function Agents() {
  const list = api.hub.listRegistry.useQuery({ category: 'agent' });
  const [filtersOpenForSmallScreens, setFiltersOpenForSmallScreens] =
    useState(false);

  return (
    <Sidebar.Root>
      <Sidebar.Sidebar
        openForSmallScreens={filtersOpenForSmallScreens}
        setOpenForSmallScreens={setFiltersOpenForSmallScreens}
      >
        <Text size="text-l">Filters</Text>

        <Flex direction="column" gap="m">
          {filters.map((filter) => (
            <Flex as="label" align="center" gap="s" key={filter}>
              <Checkbox name={filter} />
              <Text size="text-s" color="sand12">
                {filter}
              </Text>
            </Flex>
          ))}
        </Flex>
      </Sidebar.Sidebar>

      <Sidebar.Main>
        <Flex align="center" gap="m">
          <Text as="h1" size="text-2xl" style={{ marginRight: 'auto' }}>
            Agents{' '}
            {list.data && (
              <Text as="span" size="text-2xl" color="sand10" weight={400}>
                ({list.data.length})
              </Text>
            )}
          </Text>

          <BreakpointDisplay show="sidebar-small-screen">
            <Button
              label="Edit Filters"
              icon={<SlidersHorizontal weight="bold" />}
              size="small"
              fill="outline"
              onClick={() => setFiltersOpenForSmallScreens(true)}
            />
          </BreakpointDisplay>
        </Flex>

        <Table.Root>
          <Table.Head>
            <Table.Row>
              <Table.HeadCell>Agent</Table.HeadCell>
              <Table.HeadCell>Creator</Table.HeadCell>
              <Table.HeadCell>Use Case</Table.HeadCell>
              <Table.HeadCell>Tags</Table.HeadCell>
              <Table.HeadCell>Version</Table.HeadCell>
              <Table.HeadCell></Table.HeadCell>
            </Table.Row>
          </Table.Head>

          <Table.Body>
            {!list.data && <Table.PlaceholderRows />}

            {list.data?.map((item, index) => (
              <Table.Row key={index}>
                <Table.Cell href="#" style={{ minWidth: '10rem' }}>
                  <Text size="text-s" color="violet8" weight={500}>
                    {item.name}
                  </Text>

                  <div>
                    <Text size="text-xs" clampLines={1}>
                      Some description goes here
                    </Text>
                  </div>
                </Table.Cell>

                <Table.Cell>
                  <Text size="text-s">{item.namespace}</Text>
                </Table.Cell>

                <Table.Cell>
                  <Text size="text-s">DeFi</Text>
                </Table.Cell>

                <Table.Cell style={{ minWidth: '10rem' }}>
                  <Flex wrap="wrap" gap="xs">
                    <Badge label="DeFi" variant="neutral" />
                    <Badge label="Other Tag" variant="neutral" />
                    <Badge label="Super Cool" variant="neutral" />
                  </Flex>
                </Table.Cell>

                <Table.Cell>
                  <Text size="text-s">{item.version}</Text>
                </Table.Cell>

                <Table.Cell style={{ width: 1 }}>
                  <Flex gap="s">
                    <Tooltip asChild content="Run Agent">
                      <Button
                        label="Run"
                        icon={<Play weight="duotone" />}
                        size="small"
                        fill="ghost"
                      />
                    </Tooltip>

                    <Tooltip asChild content="View Repository">
                      <Button
                        label="View Repository"
                        icon={<GitFork weight="duotone" />}
                        size="small"
                        fill="ghost"
                      />
                    </Tooltip>
                  </Flex>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Sidebar.Main>
    </Sidebar.Root>
  );
}
