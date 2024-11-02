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

import { Button } from '~/components/lib/Button';
import { Card, CardList } from '~/components/lib/Card';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { PlaceholderStack } from '~/components/lib/Placeholder';
import { Sidebar } from '~/components/lib/Sidebar';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { env } from '~/env';
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
  const { updateQueryPath, queryParams } = useQueryParams(['threadId']);
  const threadId = queryParams.threadId ?? '';
  const previousThreadId = usePrevious(threadId);
  const { threads } = useThreads();
  const [removedThreadIds, setRemovedThreadIds] = useState<string[]>([]);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const filteredThreads = threads?.filter(
    (thread) => !removedThreadIds.includes(thread.id),
  );
  const isViewingAgent =
    pathname.startsWith('/agents') || env.NEXT_PUBLIC_CONSUMER_MODE;
  const removeMutation = api.hub.removeThread.useMutation();

  const currentThreadIdMatchesThread =
    !threadId || !!filteredThreads?.find((thread) => thread.id === threadId);

  const removeThread = async (thread: Thread) => {
    try {
      if (threadId === thread.id) {
        updateQueryPath({ threadId: undefined });
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

        <Tooltip asChild content="Start a new thread">
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
                  (currentThreadIdMatchesThread && threadId === thread.id) ||
                  (!currentThreadIdMatchesThread &&
                    previousThreadId === thread.id)
                    ? 'sand-0'
                    : 'sand-2'
                }
                key={thread.id}
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

                        <Dropdown.Item href={thread.agent.url}>
                          {env.NEXT_PUBLIC_CONSUMER_MODE ? (
                            <>
                              <SvgIcon icon={<Plus />} />
                              New Thread
                            </>
                          ) : (
                            <>
                              <SvgIcon icon={<Lightbulb />} />
                              View Agent
                            </>
                          )}
                        </Dropdown.Item>

                        <Dropdown.Item onSelect={() => removeThread(thread)}>
                          <SvgIcon icon={<Trash />} color="red-10" />
                          Delete Thread
                        </Dropdown.Item>
                      </Dropdown.Section>

                      {/* <Dropdown.Section>
                        <Dropdown.SectionContent>
                          <Text size="text-xs">
                            Last message sent at{' '}
                            <b>
                              <Timestamp date={thread.lastMessageAt} />
                            </b>
                          </Text>
                        </Dropdown.SectionContent>
                      </Dropdown.Section> */}
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
              You {`haven't`} started any threads yet.{' '}
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
  const updateMutation = api.hub.updateThread.useMutation();

  useEffect(() => {
    if (!form.formState.isDirty) {
      form.setValue('description', thread?.metadata.topic ?? '');

      setTimeout(() => {
        form.setFocus('description');
      });
    }
  }, [form, thread]);

  const onSubmit: SubmitHandler<EditThreadFormSchema> = async (data) => {
    // This submit handler optimistically updates environment data to make the update feel instant

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
