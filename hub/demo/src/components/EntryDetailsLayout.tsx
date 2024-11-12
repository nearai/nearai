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
  const isLatestVersion = version === 'latest';

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
            phone={{ direction: 'column', align: 'stretch', gap: 'l' }}
          >
            <Flex align="center" gap="m" style={{ marginRight: 'auto' }}>
              <ImageIcon
                size="l"
                src={currentEntry?.details.icon}
                alt={name}
                fallbackIcon={ENTRY_CATEGORY_LABELS[category].icon}
              />

              <Flex
                align="baseline"
                gap="m"
                phone={{ direction: 'column', align: 'start', gap: 'xs' }}
              >
                <Flex gap="none" direction="column">
                  <Text
                    href={`${baseUrl}/${version}`}
                    size="text-l"
                    color="sand-12"
                    decoration="none"
                  >
                    {name}
                  </Text>

                  <Text
                    href={`/profiles/${namespace}`}
                    size="text-s"
                    color="sand-11"
                    decoration="none"
                    weight={500}
                  >
                    @{namespace}
                  </Text>
                </Flex>

                <Flex align="center" gap="xs">
                  <Dropdown.Root>
                    <Dropdown.Trigger asChild>
                      <Badge
                        button
                        label={
                          isLatestVersion ? (
                            <Flex as="span" align="center" gap="s">
                              Latest
                              <Text
                                size="text-2xs"
                                color="sand-10"
                                weight={500}
                                clampLines={1}
                                style={{ maxWidth: '3rem' }}
                              >
                                {currentVersions?.[0]?.version}
                              </Text>
                            </Flex>
                          ) : (
                            <Flex as="span" align="center" gap="s">
                              Fixed
                              <Text
                                size="text-2xs"
                                color="amber-11"
                                weight={500}
                                clampLines={1}
                                style={{ maxWidth: '3rem' }}
                              >
                                {version}
                              </Text>
                            </Flex>
                          )
                        }
                        iconRight={<CaretDown />}
                        variant={isLatestVersion ? 'neutral' : 'warning'}
                      />
                    </Dropdown.Trigger>

                    <Dropdown.Content>
                      <Dropdown.Section>
                        <Dropdown.SectionContent>
                          <Text size="text-xs" weight={600} uppercase>
                            Versions
                          </Text>
                        </Dropdown.SectionContent>
                        <Dropdown.Item
                          href={`${baseUrl}/latest${activeTabPath}`}
                          key="latest"
                        >
                          Latest
                        </Dropdown.Item>
                        {currentVersions?.map((entry) => (
                          <Dropdown.Item
                            href={`${baseUrl}/${entry.version}${activeTabPath}`}
                            key={entry.version}
                          >
                            {entry.version}
                          </Dropdown.Item>
                        ))}
                      </Dropdown.Section>
                    </Dropdown.Content>
                  </Dropdown.Root>

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
                        copyTextToClipboard(`${namespace}/${name}/${version}`)
                      }
                    />
                  </Tooltip>
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
