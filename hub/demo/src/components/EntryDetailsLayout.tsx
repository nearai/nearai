'use client';

import {
  Badge,
  Button,
  copyTextToClipboard,
  Dropdown,
  Flex,
  ImageIcon,
  PlaceholderSection,
  Section,
  SvgIcon,
  Tabs,
  Text,
  Tooltip,
} from '@nearai/ui';
import {
  CaretDown,
  ChatCircleDots,
  Code,
  CodeBlock,
  GitFork,
  LockKey,
  ShareFat,
} from '@phosphor-icons/react';
import { usePathname, useRouter } from 'next/navigation';
import { type ReactElement, type ReactNode, useEffect, useState } from 'react';

import { ErrorSection } from '@/components/ErrorSection';
import { StarButton } from '@/components/StarButton';
import { env } from '@/env';
import { useConsumerModeEnabled } from '@/hooks/consumer';
import { useCurrentEntry, useCurrentEntryParams } from '@/hooks/entries';
import { ENTRY_CATEGORY_LABELS } from '@/lib/categories';
import { primaryUrlForEntry, rawFileUrlForEntry } from '@/lib/entries';
import { type EntryCategory } from '@/lib/models';

import { DevelopButton } from './DevelopButton';
import { EmbedAgentModal } from './EmbedAgentModal';
import { ForkButton } from './ForkButton';

type Props = {
  category: EntryCategory;
  children: ReactNode;
  defaultConsumerModePath?: string;
  tabs: {
    path: string;
    label: string;
    icon: ReactElement;
  }[];
};

export const ENTRY_DETAILS_LAYOUT_SIZE_NAME = 'entry-details-layout';

export const EntryDetailsLayout = ({
  category,
  children,
  defaultConsumerModePath,
  tabs,
}: Props) => {
  const { consumerModeEnabled } = useConsumerModeEnabled();
  const pathname = usePathname();
  const { namespace, name, version } = useCurrentEntryParams();
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
  const [showEmbedAgentModal, setShowEmbedAgentModal] = useState(false);

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
      {!consumerModeEnabled && (
        <Section background="sand-0" bleed gap="m" tabs>
          <Flex
            align="center"
            gap="m"
            tablet={{ direction: 'column', align: 'stretch', gap: 'l' }}
          >
            <Flex align="center" gap="m" style={{ marginRight: 'auto' }}>
              <ImageIcon
                size="l"
                src={rawFileUrlForEntry(
                  currentEntry,
                  currentEntry?.details.icon,
                )}
                alt={name}
                fallbackIcon={ENTRY_CATEGORY_LABELS[category].icon}
                padding={false}
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

                <Flex align="center" gap="s">
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

                  {currentEntry?.fork_of && (
                    <Tooltip
                      content={
                        <Text size="text-xs" color="current">
                          This {category} is a fork of{' '}
                          <Text
                            size="text-xs"
                            href={primaryUrlForEntry({
                              category: currentEntry.category,
                              namespace: currentEntry.fork_of.namespace,
                              name: currentEntry.fork_of.name,
                            })}
                          >
                            {currentEntry.fork_of.namespace}/
                            {currentEntry.fork_of.name}
                          </Text>
                        </Text>
                      }
                      root={{ disableHoverableContent: false }}
                    >
                      <SvgIcon
                        icon={<GitFork weight="fill" />}
                        size="xs"
                        color="sand-9"
                        style={{ cursor: 'help' }}
                      />
                    </Tooltip>
                  )}

                  {currentEntry?.details.private_source && (
                    <Tooltip
                      content={`The source code for this ${category} is private`}
                    >
                      <SvgIcon
                        icon={<LockKey weight="fill" />}
                        size="xs"
                        color="sand-9"
                        style={{ cursor: 'help' }}
                      />
                    </Tooltip>
                  )}
                </Flex>
              </Flex>
            </Flex>

            <Flex align="center" gap="s" wrap="wrap">
              <DevelopButton entry={currentEntry} />
              <StarButton entry={currentEntry} variant="detailed" />
              <ForkButton entry={currentEntry} variant="detailed" />

              {category === 'agent' ? (
                <Dropdown.Root>
                  <Tooltip asChild content={`Share or embed this ${category}`}>
                    <Dropdown.Trigger asChild>
                      <Button
                        label="Share"
                        icon={<SvgIcon size="xs" icon={<ShareFat />} />}
                        size="small"
                        fill="outline"
                      />
                    </Dropdown.Trigger>
                  </Tooltip>

                  <Dropdown.Content>
                    <Dropdown.Section>
                      <Dropdown.Item
                        onSelect={() =>
                          currentEntry &&
                          copyTextToClipboard(
                            `https://app.near.ai${primaryUrlForEntry(currentEntry)}`,
                          )
                        }
                      >
                        <SvgIcon icon={<CodeBlock />} />
                        Copy Developer URL
                      </Dropdown.Item>

                      <Dropdown.Item
                        onSelect={() =>
                          currentEntry &&
                          copyTextToClipboard(
                            `https://chat.near.ai${primaryUrlForEntry(currentEntry)}`,
                          )
                        }
                      >
                        <SvgIcon icon={<ChatCircleDots />} />
                        Copy Chat URL
                      </Dropdown.Item>

                      <Dropdown.Item
                        onSelect={() => setShowEmbedAgentModal(true)}
                      >
                        <SvgIcon icon={<Code />} />
                        Embed Agent
                      </Dropdown.Item>
                    </Dropdown.Section>
                  </Dropdown.Content>
                </Dropdown.Root>
              ) : (
                <Tooltip asChild content={`Share this ${category}`}>
                  <Button
                    label="Share"
                    icon={<SvgIcon size="xs" icon={<ShareFat />} />}
                    size="small"
                    fill="outline"
                    onClick={() =>
                      currentEntry &&
                      copyTextToClipboard(
                        `https://app.near.ai${primaryUrlForEntry(currentEntry)}`,
                        `Shareable URL for ${currentEntry.name}`,
                      )
                    }
                  />
                </Tooltip>
              )}
            </Flex>
          </Flex>

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
        </Section>
      )}

      {(!currentEntry || shouldRedirectToDefaultConsumerPath) && (
        <PlaceholderSection />
      )}

      {!shouldRedirectToDefaultConsumerPath && children}

      {category === 'agent' && (
        <EmbedAgentModal
          entry={currentEntry}
          isOpen={showEmbedAgentModal}
          setIsOpen={setShowEmbedAgentModal}
        />
      )}
    </>
  );
};
