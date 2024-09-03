'use client';

import {
  BookOpenText,
  CaretDown,
  CodeBlock,
  Play,
} from '@phosphor-icons/react';
import { usePathname } from 'next/navigation';
import { type ReactNode } from 'react';

import { Badge } from '~/components/lib/Badge';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { PlaceholderSection } from '~/components/lib/Placeholder';
import { Section } from '~/components/lib/Section';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Tabs } from '~/components/lib/Tabs';
import { Text } from '~/components/lib/Text';
import { useCurrentResource, useResourceParams } from '~/hooks/resources';

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathSegments = usePathname().split('/');
  const { namespace, name, version } = useResourceParams();
  const { currentResource, currentVersions } = useCurrentResource('agent');
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
        <Flex align="center" gap="m">
          <Text as="h1" size="text-l">
            {namespace} / {name}
          </Text>

          <Dropdown.Root>
            <Dropdown.Trigger asChild>
              <Badge button label={version} iconRight={<CaretDown />} />
            </Dropdown.Trigger>

            <Dropdown.Content>
              <Dropdown.Section>
                <Dropdown.SectionContent>
                  <Text size="text-xs">Versions</Text>
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
