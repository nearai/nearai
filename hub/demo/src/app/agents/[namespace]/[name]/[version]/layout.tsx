'use client';

import {
  BookOpenText,
  CaretDown,
  CodeBlock,
  Play,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { type ReactNode } from 'react';

import { Badge } from '~/components/lib/Badge';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { ImageIcon } from '~/components/lib/ImageIcon';
import { PlaceholderSection } from '~/components/lib/Placeholder';
import { Section } from '~/components/lib/Section';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Tabs } from '~/components/lib/Tabs';
import { Text } from '~/components/lib/Text';
import { StarButton } from '~/components/StarButton';
import {
  useCurrentRegistryEntry,
  useRegistryEntryParams,
} from '~/hooks/registry';
import { CATEGORY_LABELS } from '~/utils/category';

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathSegments = usePathname().split('/');
  const { namespace, name, version } = useRegistryEntryParams();
  const { currentResource, currentVersions } = useCurrentRegistryEntry('agent');
  const baseUrl = `/agents/${namespace}/${name}`;
  let activeTab: 'overview' | 'run' | 'source' = 'overview';

  if (pathSegments.at(-1) === 'run') {
    activeTab = 'run';
  } else if (pathSegments.at(-1) === 'source') {
    activeTab = 'source';
  }

  return (
    <>
      <Section background="sand-0" bleed gap="m" tabs>
        <Flex
          align="center"
          gap="m"
          phone={{ direction: 'column', align: 'start', gap: 'l' }}
        >
          <Flex
            align="center"
            gap="m"
            style={{ width: '100%' }}
            phone={{ justify: 'space-between' }}
          >
            <Flex align="center" gap="m">
              <ImageIcon
                size="l"
                src={currentResource?.details.icon}
                alt={name}
                fallbackIcon={CATEGORY_LABELS.agent.icon}
              />

              <Flex gap="none" direction="column" align="start">
                <Flex align="center" gap="m">
                  <Link href={baseUrl}>
                    <Text as="h1" size="text-l" weight={600} color="sand-12">
                      {name}
                    </Text>
                  </Link>

                  <Dropdown.Root>
                    <Dropdown.Trigger asChild>
                      <Badge
                        button
                        label={version}
                        iconRight={<CaretDown />}
                        variant="neutral"
                      />
                    </Dropdown.Trigger>

                    <Dropdown.Content>
                      <Dropdown.Section>
                        <Dropdown.SectionContent>
                          <Text size="text-xs" weight={600} uppercase>
                            Versions
                          </Text>
                        </Dropdown.SectionContent>

                        {currentVersions?.map((item) => (
                          <Dropdown.Item
                            href={`${baseUrl}/${item.version}`}
                            key={item.version}
                          >
                            {item.version}
                          </Dropdown.Item>
                        ))}
                      </Dropdown.Section>
                    </Dropdown.Content>
                  </Dropdown.Root>
                </Flex>

                <Link
                  href={`/profiles/${namespace}`}
                  style={{ marginTop: '-0.25rem' }}
                >
                  <Text size="text-s" weight={500}>
                    @{namespace}
                  </Text>
                </Link>
              </Flex>
            </Flex>
          </Flex>

          <StarButton item={currentResource} variant="detailed" />
        </Flex>

        <Tabs.Root value={activeTab}>
          <Tabs.List>
            <Tabs.Trigger href={`${baseUrl}/${version}`} value="overview">
              <SvgIcon icon={<BookOpenText fill="bold" />} />
              Overview
            </Tabs.Trigger>

            <Tabs.Trigger href={`${baseUrl}/${version}/source`} value="source">
              <SvgIcon icon={<CodeBlock fill="bold" />} />
              Source
            </Tabs.Trigger>

            <Tabs.Trigger href={`${baseUrl}/${version}/run`} value="run">
              <SvgIcon icon={<Play fill="bold" />} />
              Run
            </Tabs.Trigger>
          </Tabs.List>
        </Tabs.Root>
      </Section>

      {!currentResource && <PlaceholderSection />}

      {children}
    </>
  );
}
