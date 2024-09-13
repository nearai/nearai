'use client';

import {
  DotsThreeVertical,
  Link as LinkIcon,
  Plus,
  Trash,
} from '@phosphor-icons/react';
import { usePrevious } from '@uidotdev/usehooks';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge } from '~/components/lib/Badge';
import { Button } from '~/components/lib/Button';
import { Card, CardList } from '~/components/lib/Card';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { PlaceholderStack } from '~/components/lib/Placeholder';
import { Sidebar } from '~/components/lib/Sidebar';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Text } from '~/components/lib/Text';
import { Timestamp } from '~/components/lib/Timestamp';
import { Tooltip } from '~/components/lib/Tooltip';
import { type Thread, useThreads } from '~/hooks/threads';
import { useQueryParams } from '~/hooks/url';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';
import { handleClientError } from '~/utils/error';

type Props = {
  onRequestNewThread: () => unknown;
  openForSmallScreens: boolean;
  setOpenForSmallScreens: (open: boolean) => unknown;
};

export const ThreadsSidebar = ({
  onRequestNewThread,
  openForSmallScreens,
  setOpenForSmallScreens,
}: Props) => {
  const router = useRouter();
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { createQueryPath, queryParams } = useQueryParams(['environmentId']);
  const environmentId = queryParams.environmentId ?? '';
  const previousEnvironmentId = usePrevious(environmentId);
  const { threads } = useThreads();
  const [removedEnvironmentIds, setRemovedEnvironmentIds] = useState<string[]>(
    [],
  );
  const filteredThreads = threads?.filter(
    (thread) => !removedEnvironmentIds.includes(thread.environmentId),
  );
  const isViewingAgent = pathname.startsWith('/agents');
  const updateMetadataMutation = api.hub.updateMetadata.useMutation();

  const currentEnvironmentIdMatchesThread = !!filteredThreads?.find(
    (thread) => thread.environmentId === environmentId,
  );

  const removeThread = async (thread: Thread) => {
    try {
      if (environmentId === thread.environmentId) {
        router.replace(createQueryPath({ environmentId: undefined }));
      }

      setRemovedEnvironmentIds((value) => [...value, thread.environmentId]);

      for (const {
        namespace,
        name,
        version,
        ...environment
      } of thread.environments) {
        await updateMetadataMutation.mutateAsync({
          name,
          namespace,
          version,
          metadata: {
            ...environment,
            show_entry: false,
          },
        });
      }
    } catch (error) {
      handleClientError({ error, title: 'Failed to delete thread' });
    }
  };

  useEffect(() => {
    setOpenForSmallScreens(false);
  }, [setOpenForSmallScreens, environmentId]);

  if (!isAuthenticated) return null;

  return (
    <Sidebar.Sidebar
      openForSmallScreens={openForSmallScreens}
      setOpenForSmallScreens={setOpenForSmallScreens}
    >
      <Flex align="center" gap="s">
        <Text size="text-xs" weight={500} uppercase>
          Threads
        </Text>

        <Tooltip asChild content="Start a new agent thread">
          <Button
            label="New Thread"
            icon={<Plus weight="bold" />}
            variant="affirmative"
            size="x-small"
            fill="ghost"
            onClick={onRequestNewThread}
          />
        </Tooltip>
      </Flex>

      {filteredThreads?.length ? (
        <Sidebar.SidebarContentBleed>
          <CardList>
            {filteredThreads.map((thread) => (
              <Card
                href={thread.agent.url}
                padding="s"
                paddingInline="m"
                gap="xs"
                background={
                  (currentEnvironmentIdMatchesThread &&
                    environmentId === thread.environmentId) ||
                  (!currentEnvironmentIdMatchesThread &&
                    previousEnvironmentId === thread.environmentId)
                    ? 'sand-0'
                    : 'sand-2'
                }
                key={thread.environmentId}
              >
                <Flex align="center" gap="s">
                  <Text
                    as="span"
                    size="text-s"
                    weight={500}
                    color="sand-12"
                    clickableHighlight
                    style={{ marginRight: 'auto' }}
                  >
                    {thread.agent.name} {thread.agent.version}
                  </Text>

                  <Tooltip
                    asChild
                    content={`${thread.messageCount} prompt${thread.messageCount !== 1 ? 's' : ''}`}
                    key={thread.environmentId}
                  >
                    <Badge
                      label={thread.messageCount}
                      count
                      variant="neutral"
                    />
                  </Tooltip>
                </Flex>

                <Flex align="center" gap="s">
                  <Text
                    size="text-xs"
                    clampLines={1}
                    style={{ marginRight: 'auto' }}
                  >
                    @{thread.agent.namespace}
                  </Text>

                  <Text size="text-xs" noWrap style={{ flexShrink: 0 }}>
                    <Timestamp date={thread.lastMessageAt} />
                  </Text>

                  <Dropdown.Root>
                    <Dropdown.Trigger asChild>
                      <Button
                        label="Manage Thread"
                        icon={<DotsThreeVertical weight="bold" />}
                        size="x-small"
                        fill="ghost"
                      />
                    </Dropdown.Trigger>

                    <Dropdown.Content sideOffset={0}>
                      <Dropdown.Section>
                        <Dropdown.Item
                          onSelect={() =>
                            copyTextToClipboard(
                              `${window.location.origin}${thread.agent.url}`,
                            )
                          }
                        >
                          <SvgIcon icon={<LinkIcon />} />
                          Copy Link
                        </Dropdown.Item>

                        <Dropdown.Item onSelect={() => removeThread(thread)}>
                          <SvgIcon icon={<Trash />} color="red-10" />
                          Delete
                        </Dropdown.Item>
                      </Dropdown.Section>
                    </Dropdown.Content>
                  </Dropdown.Root>
                </Flex>
              </Card>
            ))}
          </CardList>
        </Sidebar.SidebarContentBleed>
      ) : (
        <>
          {filteredThreads ? (
            <Text size="text-s">
              You {`haven't`} started any agent threads yet.{' '}
              {isViewingAgent ? (
                <>Submit a message to start your first thread.</>
              ) : (
                <>
                  <br />
                  <Link href="/agents">
                    <Text
                      as="span"
                      size="text-s"
                      color="violet-11"
                      weight={500}
                    >
                      Select an agent
                    </Text>
                  </Link>{' '}
                  to start your first thread.
                </>
              )}
            </Text>
          ) : (
            <PlaceholderStack />
          )}
        </>
      )}
    </Sidebar.Sidebar>
  );
};
