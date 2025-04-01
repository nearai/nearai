'use client';

import {
  Badge,
  Button,
  Card,
  CardList,
  copyTextToClipboard,
  Dialog,
  Dropdown,
  Flex,
  Form,
  handleClientError,
  Input,
  PlaceholderStack,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import {
  DotsThree,
  Lightbulb,
  Link as LinkIcon,
  Pencil,
  Plus,
  Tag,
  Trash,
} from '@phosphor-icons/react';
import { useEffect, useState } from 'react';
import { type SubmitHandler, useForm } from 'react-hook-form';

import { Sidebar } from '@/components/lib/Sidebar';
import { useConsumerModeEnabled } from '@/hooks/consumer';
import { type ThreadSummary, useThreads } from '@/hooks/threads';
import { useQueryParams } from '@/hooks/url';
import { useAuthStore } from '@/stores/auth';
import { trpc } from '@/trpc/TRPCProvider';

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
  const { consumerModeEnabled } = useConsumerModeEnabled();
  const auth = useAuthStore((store) => store.auth);
  const { updateQueryPath, queryParams } = useQueryParams(['threadId']);
  const threadId = queryParams.threadId ?? '';
  const { threads } = useThreads();
  const [removedThreadIds, setRemovedThreadIds] = useState<string[]>([]);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const filteredThreads = threads?.filter(
    (thread) => !removedThreadIds.includes(thread.id),
  );
  const removeMutation = trpc.hub.removeThread.useMutation();

  const [showAllThreads, setShowAllThreads] = useState(false);
  const threadsToDisplay = showAllThreads
    ? filteredThreads
    : filteredThreads?.slice(0, 50);
  const hiddenThreadsCount =
    (filteredThreads?.length ?? 0) - (threadsToDisplay?.length ?? 0);

  const removeThread = async (thread: ThreadSummary) => {
    try {
      if (threadId === thread.id) {
        updateQueryPath({ threadId: null });
      }

      setRemovedThreadIds((value) => [...value, thread.id]);

      await removeMutation.mutateAsync({
        threadId: thread.id,
      });
    } catch (error) {
      handleClientError({ error, title: 'Failed to delete thread' });
    }
  };

  useEffect(() => {
    setOpenForSmallScreens(false);
  }, [setOpenForSmallScreens, threadId]);

  if (!auth) return null;

  return (
    <Sidebar.Sidebar
      openForSmallScreens={openForSmallScreens}
      setOpenForSmallScreens={setOpenForSmallScreens}
    >
      <Flex align="center" gap="s">
        <Text size="text-xs" weight={600} uppercase>
          Threads
        </Text>

        <Tooltip asChild content="Start a new thread">
          <Button
            label="New Thread"
            icon={<Plus weight="bold" />}
            variant="affirmative"
            fill="ghost"
            size="x-small"
            onClick={onRequestNewThread}
          />
        </Tooltip>
      </Flex>

      {filteredThreads?.length && threadsToDisplay?.length ? (
        <>
          <Sidebar.SidebarContentBleed>
            <CardList>
              {threadsToDisplay.map((thread) => (
                <Card
                  href={thread.url}
                  padding="s"
                  paddingInline="m"
                  background={threadId === thread.id ? 'sand-0' : 'sand-2'}
                  key={thread.id}
                  onDoubleClick={() => setEditingThreadId(thread.id)}
                >
                  <Flex direction="column">
                    <Flex align="center" gap="s">
                      <Text
                        as="span"
                        size="text-s"
                        weight={500}
                        color="sand-12"
                        clampLines={1}
                        style={{ marginRight: 'auto' }}
                      >
                        {thread.metadata.topic}
                      </Text>

                      {/* <Tooltip
                    asChild
                    content={`${thread.messageCount} message${thread.messageCount === 1 ? '' : 's'} sent`}
                    key={thread.id}
                  >
                    <Badge
                      label={thread.messageCount}
                      count
                      variant="neutral"
                    />
                  </Tooltip> */}
                    </Flex>

                    <Flex align="center" gap="s">
                      <Text
                        size="text-2xs"
                        clampLines={1}
                        style={{ marginRight: 'auto' }}
                      >
                        {thread.agent.namespace}/{thread.agent.name}
                      </Text>

                      {thread.agent.version !== 'latest' && (
                        <Tooltip
                          content={`This thread is fixed to a specific agent version: ${thread.agent.version}`}
                        >
                          <Badge
                            size="small"
                            iconLeft={<Tag />}
                            label={thread.agent.version}
                            style={{
                              maxWidth: '4.5rem',
                            }}
                            variant="warning"
                          />
                        </Tooltip>
                      )}

                      <Dropdown.Root>
                        <Dropdown.Trigger asChild>
                          <Button
                            label="Manage Thread"
                            icon={<DotsThree weight="bold" />}
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
                              onSelect={() => setEditingThreadId(thread.id)}
                            >
                              <SvgIcon icon={<Pencil />} />
                              Rename Thread
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

                            {!consumerModeEnabled && (
                              <Dropdown.Item href={thread.agent.url}>
                                <SvgIcon icon={<Lightbulb />} />
                                View Agent Details
                              </Dropdown.Item>
                            )}

                            <Dropdown.Item
                              onSelect={() => removeThread(thread)}
                            >
                              <SvgIcon icon={<Trash />} color="red-10" />
                              Delete Thread
                            </Dropdown.Item>
                          </Dropdown.Section>
                        </Dropdown.Content>
                      </Dropdown.Root>
                    </Flex>
                  </Flex>
                </Card>
              ))}
            </CardList>
          </Sidebar.SidebarContentBleed>

          {hiddenThreadsCount > 0 && (
            <Button
              size="small"
              fill="outline"
              label="Load More Threads"
              count={hiddenThreadsCount}
              onClick={() => setShowAllThreads(true)}
            />
          )}
        </>
      ) : (
        <>
          {filteredThreads ? (
            <>
              <Text size="text-s">
                Submit a message to start your first thread.
              </Text>

              {!consumerModeEnabled && (
                <Button
                  label="Browse Agents"
                  href="/agents"
                  size="small"
                  variant="secondary"
                />
              )}
            </>
          ) : (
            <PlaceholderStack />
          )}
        </>
      )}

      <Dialog.Root
        open={!!editingThreadId}
        onOpenChange={() => setEditingThreadId(null)}
      >
        <Dialog.Content title="Rename Thread" size="s">
          <EditThreadForm
            threadThreadId={editingThreadId}
            onFinish={() => setEditingThreadId(null)}
          />
        </Dialog.Content>
      </Dialog.Root>
    </Sidebar.Sidebar>
  );
};

type EditThreadFormProps = {
  threadThreadId: string | null;
  onFinish: () => unknown;
};

type EditThreadFormSchema = {
  description: string;
};

const EditThreadForm = ({ threadThreadId, onFinish }: EditThreadFormProps) => {
  const form = useForm<EditThreadFormSchema>({});
  const { setThreadData, threads } = useThreads();
  const thread = threads?.find((t) => t.id === threadThreadId);
  const updateMutation = trpc.hub.updateThread.useMutation();

  useEffect(() => {
    if (!form.formState.isDirty) {
      form.setValue('description', thread?.metadata.topic ?? '');

      setTimeout(() => {
        form.setFocus('description');
      });
    }
  }, [form, thread]);

  const onSubmit: SubmitHandler<EditThreadFormSchema> = async (data) => {
    // This submit handler optimistically updates thread data to make the update feel instant

    try {
      if (!thread) return;

      const updates = {
        metadata: {
          ...thread.metadata,
          topic: data.description,
        },
      };

      setThreadData(thread.id, updates);

      void updateMutation.mutateAsync({
        threadId: thread.id,
        ...updates,
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
