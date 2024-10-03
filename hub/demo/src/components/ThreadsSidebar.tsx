'use client';

import {
  DotsThreeVertical,
  Lightbulb,
  Link as LinkIcon,
  Pencil,
  Plus,
  Trash,
} from '@phosphor-icons/react';
import { usePrevious } from '@uidotdev/usehooks';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { type SubmitHandler, useForm } from 'react-hook-form';

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

import { Dialog } from './lib/Dialog';
import { Form } from './lib/Form';
import { Input } from './lib/Input';

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
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { updateQueryPath, queryParams } = useQueryParams(['environmentId']);
  const environmentId = queryParams.environmentId ?? '';
  const previousEnvironmentId = usePrevious(environmentId);
  const { threads } = useThreads();
  const [removedEnvironmentIds, setRemovedEnvironmentIds] = useState<string[]>(
    [],
  );
  const [editingThreadEnvironmentId, setEditingThreadEnvironmentId] = useState<
    string | null
  >(null);
  const filteredThreads = threads?.filter(
    (thread) => !removedEnvironmentIds.includes(thread.environmentId),
  );
  const isViewingAgent = pathname.startsWith('/agents');
  const updateMutation = api.hub.updateMetadata.useMutation();

  const currentEnvironmentIdMatchesThread =
    !environmentId ||
    !!filteredThreads?.find((thread) => thread.environmentId === environmentId);

  const removeThread = async (thread: Thread) => {
    try {
      if (environmentId === thread.environmentId) {
        updateQueryPath({ environmentId: undefined });
      }

      setRemovedEnvironmentIds((value) => [...value, thread.environmentId]);

      for (const {
        namespace,
        name,
        version,
        ...environment
      } of thread.environments) {
        await updateMutation.mutateAsync({
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
        <Text size="text-xs" weight={600} uppercase>
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
                href={thread.url}
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
                    clampLines={1}
                    style={{ marginRight: 'auto' }}
                  >
                    {thread.description}
                  </Text>

                  <Tooltip
                    asChild
                    content={`${thread.messageCount} message${thread.messageCount === 1 ? '' : 's'} sent`}
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
                    {thread.agent.namespace}/{thread.agent.name}/
                    {thread.agent.version}
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
                        <Dropdown.SectionContent>
                          <Text size="text-xs" weight={600} uppercase>
                            Thread
                          </Text>
                        </Dropdown.SectionContent>
                      </Dropdown.Section>

                      <Dropdown.Section>
                        <Dropdown.Item
                          onSelect={() =>
                            setEditingThreadEnvironmentId(thread.environmentId)
                          }
                        >
                          <SvgIcon icon={<Pencil />} />
                          Rename Thread
                        </Dropdown.Item>

                        <Dropdown.Item href={thread.agent.url}>
                          <SvgIcon icon={<Lightbulb />} />
                          View Agent
                        </Dropdown.Item>

                        <Dropdown.Item
                          onSelect={() =>
                            copyTextToClipboard(
                              `${window.location.origin}${thread.url}`,
                            )
                          }
                        >
                          <SvgIcon icon={<LinkIcon />} />
                          Copy Thread Link
                        </Dropdown.Item>

                        <Dropdown.Item onSelect={() => removeThread(thread)}>
                          <SvgIcon icon={<Trash />} color="red-10" />
                          Delete Thread
                        </Dropdown.Item>
                      </Dropdown.Section>

                      <Dropdown.Section>
                        <Dropdown.SectionContent>
                          <Text size="text-xs">
                            Last prompt at{' '}
                            <b>
                              <Timestamp date={thread.lastMessageAt} />
                            </b>
                          </Text>
                        </Dropdown.SectionContent>
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

      <Dialog.Root
        open={!!editingThreadEnvironmentId}
        onOpenChange={() => setEditingThreadEnvironmentId(null)}
      >
        <Dialog.Content title="Rename Thread" size="s">
          <EditThreadForm
            threadEnvironmentId={editingThreadEnvironmentId}
            onFinish={() => setEditingThreadEnvironmentId(null)}
          />
        </Dialog.Content>
      </Dialog.Root>
    </Sidebar.Sidebar>
  );
};

type EditThreadFormProps = {
  threadEnvironmentId: string | null;
  onFinish: () => unknown;
};

type EditThreadFormSchema = {
  description: string;
};

const EditThreadForm = ({
  threadEnvironmentId,
  onFinish,
}: EditThreadFormProps) => {
  const form = useForm<EditThreadFormSchema>({});
  const { setThreadEnvironmentData, threads } = useThreads();
  const thread = threads?.find((t) => t.environmentId === threadEnvironmentId);
  const updateMutation = api.hub.updateMetadata.useMutation();

  useEffect(() => {
    if (!form.formState.isDirty) {
      form.setValue('description', thread?.description ?? '');

      setTimeout(() => {
        form.setFocus('description');
      });
    }
  }, [form, thread]);

  const onSubmit: SubmitHandler<EditThreadFormSchema> = async (data) => {
    // This submit handler optimistically updates environment data to make the update feel instant

    try {
      const firstEnvironment = thread?.environments[0];
      if (!firstEnvironment) return;
      const { namespace, name, version, ...environment } = firstEnvironment;

      const updates = {
        description: data.description,
      };

      setThreadEnvironmentData(firstEnvironment.id, updates);

      void updateMutation.mutateAsync({
        name,
        namespace,
        version,
        metadata: {
          ...environment,
          ...updates,
        },
      });
    } catch (error) {
      handleClientError({ error });
    }

    onFinish();
  };

  return (
    <Form onSubmit={form.handleSubmit(onSubmit)}>
      <Flex direction="column" gap="l">
        <Input label="Name" type="text" {...form.register('description')} />

        <Flex align="center" justify="space-between">
          <Button
            label="Cancel"
            variant="secondary"
            fill="outline"
            onClick={onFinish}
          />
          <Button label="Save" variant="affirmative" type="submit" />
        </Flex>
      </Flex>
    </Form>
  );
};
