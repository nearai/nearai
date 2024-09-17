'use client';

import { ArrowsDownUp, SlidersHorizontal } from '@phosphor-icons/react';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge } from '~/components/lib/Badge';
import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Checkbox, CheckboxGroup } from '~/components/lib/Checkbox';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { HR } from '~/components/lib/HorizontalRule';
import { PlaceholderSection } from '~/components/lib/Placeholder';
import { Sidebar } from '~/components/lib/Sidebar';
import { Text } from '~/components/lib/Text';
import { ResourceCard } from '~/components/ResourceCard';
import { useProfileParams } from '~/hooks/profile';
import { useQueryParams } from '~/hooks/url';
import { type RegistryCategory } from '~/server/api/routers/hub';
import { api } from '~/trpc/react';
import { CATEGORY_LABELS } from '~/utils/category';
import { toTitleCase } from '~/utils/string';

const categories: RegistryCategory[] = [
  'agent',
  'benchmark',
  'dataset',
  'model',
];

export default function ProfilePage() {
  const pathSegments = usePathname().split('/');
  const starred = pathSegments.at(-1) === 'starred';
  const { accountId } = useProfileParams();
  const { updateQueryPath, queryParams } = useQueryParams(['category', 'sort']);
  const sort = queryParams.sort ?? 'stars';
  const [sidebarOpenForSmallScreens, setSidebarOpenForSmallScreens] =
    useState(false);

  const list = api.hub.registryEntries.useQuery({
    namespace: starred ? undefined : accountId,
    starredBy: starred ? accountId : undefined,
  });

  const allPublished = list.data?.filter((item) =>
    categories.includes(item.category as RegistryCategory),
  );

  const filteredPublished = queryParams.category
    ? allPublished?.filter((item) => item.category === queryParams.category)
    : allPublished;

  useEffect(() => {
    setSidebarOpenForSmallScreens(false);
  }, [queryParams.category]);

  switch (sort) {
    case 'stars':
      allPublished?.sort((a, b) => {
        let sort = b.num_stars - a.num_stars;
        if (sort === 0) sort = a.name.localeCompare(b.name);
        return sort;
      });
      break;
    default:
      allPublished?.sort((a, b) => a.name.localeCompare(b.name));
  }

  if (!allPublished || !filteredPublished) return <PlaceholderSection />;

  return (
    <>
      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={sidebarOpenForSmallScreens}
          setOpenForSmallScreens={setSidebarOpenForSmallScreens}
        >
          <CheckboxGroup name="resourceTypeFilter">
            <Flex as="label" align="center" gap="s">
              <Checkbox
                name="resourceTypeFilter"
                value="all"
                type="radio"
                checked={!queryParams.category}
                onChange={() => updateQueryPath({ category: undefined })}
              />
              <Text>All</Text>
            </Flex>

            {categories.map((category) => (
              <Flex as="label" align="center" gap="s" key={category}>
                <Checkbox
                  name="resourceTypeFilter"
                  value={category}
                  type="radio"
                  checked={queryParams.category === category}
                  onChange={() => updateQueryPath({ category: category })}
                />
                <Text>{CATEGORY_LABELS[category].label}</Text>
                <Badge
                  label={
                    allPublished.filter((item) => item.category === category)
                      .length
                  }
                  count
                  variant="neutral-alpha"
                  size="small"
                />
              </Flex>
            ))}
          </CheckboxGroup>

          <HR />

          <Flex gap="m" align="center">
            <Text size="text-xs">Sort by:</Text>
            <Dropdown.Root>
              <Dropdown.Trigger asChild>
                <Badge
                  button
                  label={toTitleCase(sort)}
                  iconLeft={<ArrowsDownUp />}
                  variant="neutral"
                />
              </Dropdown.Trigger>

              <Dropdown.Content align="start">
                <Dropdown.Section>
                  <Dropdown.SectionContent>
                    <Text size="text-xs">Sort By</Text>
                  </Dropdown.SectionContent>

                  <Dropdown.Item
                    onSelect={() => updateQueryPath({ sort: 'name' })}
                  >
                    Name
                  </Dropdown.Item>

                  <Dropdown.Item
                    onSelect={() => updateQueryPath({ sort: 'stars' })}
                  >
                    Stars
                  </Dropdown.Item>
                </Dropdown.Section>
              </Dropdown.Content>
            </Dropdown.Root>
          </Flex>
        </Sidebar.Sidebar>

        <Sidebar.Main>
          <Flex direction="column" gap="m">
            <BreakpointDisplay show="sidebar-small-screen">
              <Button
                label={`Filter (${
                  queryParams.category
                    ? CATEGORY_LABELS[queryParams.category]?.label ?? 'Unknown'
                    : 'All'
                })`}
                iconLeft={<SlidersHorizontal weight="bold" />}
                size="small"
                fill="outline"
                onClick={() => setSidebarOpenForSmallScreens(true)}
                style={{ width: '100%' }}
              />
            </BreakpointDisplay>

            {filteredPublished.map((item) => (
              <ResourceCard item={item} key={item.id} />
            ))}

            {!allPublished.length ? (
              <Text size="text-s">
                This account has not {starred ? 'starred' : 'published'} any
                resources yet.
              </Text>
            ) : !filteredPublished.length ? (
              <Text size="text-s">
                This account has not {starred ? 'starred' : 'published'} any
                resources that match your selected filters.
              </Text>
            ) : undefined}
          </Flex>
        </Sidebar.Main>
      </Sidebar.Root>
    </>
  );
}