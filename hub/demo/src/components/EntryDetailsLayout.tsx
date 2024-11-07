'use client';

import {
  Badge,
  Button,
  Dropdown,
  Flex,
  ImageIcon,
  PlaceholderSection,
  Section,
  SvgIcon,
  Tabs,
  Text,
  Tooltip,
} from '@near-pagoda/ui';
import { CaretDown, Copy } from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { type ReactElement, type ReactNode, useEffect } from 'react';

import { ErrorSection } from '~/components/ErrorSection';
import { StarButton } from '~/components/StarButton';
import { env } from '~/env';
import { useCurrentEntry, useEntryParams } from '~/hooks/entries';
import { ENTRY_CATEGORY_LABELS } from '~/lib/entries';
import { type EntryCategory } from '~/lib/models';
import { copyTextToClipboard } from '~/utils/clipboard';

type Props = {
  category: EntryCategory;
  children: ReactNode;
  defaultConsumerModePath?: string;
  tabs:
    | {
        path: string;
        label: string;
        icon: ReactElement;
      }[]
    | null;
};

export const EntryDetailsLayout = ({
  category,
  children,
  defaultConsumerModePath,
  tabs,
}: Props) => {
  const pathname = usePathname();
  const { namespace, name, version } = useEntryParams();
  const { currentEntry, currentEntryIsHidden, currentVersions } =
    useCurrentEntry(category);
  const baseUrl = `/${category}s/${namespace}/${name}`;
  const activeTabPath = pathname.replace(`${baseUrl}/${version}`, '');
  const router = useRouter();
  const defaultConsumerPath = `${baseUrl}/${version}${defaultConsumerModePath}`;
  const shouldRedirectToDefaultConsumerPath =
    env.NEXT_PUBLIC_CONSUMER_MODE &&
    defaultConsumerModePath &&
    !pathname.includes(defaultConsumerPath);

  useEffect(() => {
    if (shouldRedirectToDefaultConsumerPath) {
      router.replace(defaultConsumerPath);
    }
  }, [defaultConsumerPath, router, shouldRedirectToDefaultConsumerPath]);

  if (currentEntryIsHidden) {
    return <ErrorSection error="404" />;
  }

  return (
    <>
      {!env.NEXT_PUBLIC_CONSUMER_MODE && (
        <Section background="sand-0" bleed gap="m" tabs={!!tabs}>
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
                  src={currentEntry?.details.icon}
                  alt={name}
                  fallbackIcon={ENTRY_CATEGORY_LABELS[category].icon}
                />

                <Flex gap="none" direction="column" align="start">
                  <Flex align="center" gap="m">
                    <Link href={`${baseUrl}/${version}`}>
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

                          {currentVersions?.map((entry) => (
                            <Dropdown.Item
                              href={`${baseUrl}/${entry.version}`}
                              key={entry.version}
                            >
                              {entry.version}
                            </Dropdown.Item>
                          ))}
                        </Dropdown.Section>
                      </Dropdown.Content>
                    </Dropdown.Root>

                    {!env.NEXT_PUBLIC_CONSUMER_MODE && (
                      <Tooltip
                        asChild
                        content={`Copy ${category} path to clipboard`}
                      >
                        <Button
                          label="Copy"
                          icon={<Copy />}
                          size="x-small"
                          variant="secondary"
                          fill="ghost"
                          onClick={() =>
                            copyTextToClipboard(
                              `${namespace}/${name}/${version}`,
                            )
                          }
                        />
                      </Tooltip>
                    )}
                  </Flex>

                  <Link
                    href={`/profiles/${namespace}`}
                    style={{ marginTop: '-0.1rem' }}
                  >
                    <Text size="text-s" weight={500}>
                      @{namespace}
                    </Text>
                  </Link>
                </Flex>
              </Flex>
            </Flex>

            <StarButton entry={currentEntry} variant="detailed" />
          </Flex>

          {tabs && (
            <Tabs.Root value={activeTabPath}>
              <Tabs.List>
                {tabs.map((tab) => (
                  <Tabs.Trigger
                    href={`${baseUrl}/${version}${tab.path}`}
                    value={tab.path}
                    key={tab.path}
                  >
                    <SvgIcon icon={tab.icon} />
                    {tab.label}
                  </Tabs.Trigger>
                ))}
              </Tabs.List>
            </Tabs.Root>
          )}
        </Section>
      )}

      {(!currentEntry || shouldRedirectToDefaultConsumerPath) && (
        <PlaceholderSection />
      )}

      {!shouldRedirectToDefaultConsumerPath && children}
    </>
  );
};
