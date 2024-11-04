'use client';

import {
  ArrowRight,
  Chats,
  Copy,
  Eye,
  Gear,
  List,
} from '@phosphor-icons/react';
import { useMutation } from '@tanstack/react-query';
import {
  type KeyboardEventHandler,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import { Controller, type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { AgentPermissionsModal } from '~/components/AgentPermissionsModal';
import { AgentWelcome } from '~/components/AgentWelcome';
import { EntryEnvironmentVariables } from '~/components/EntryEnvironmentVariables';
import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Card, CardList } from '~/components/lib/Card';
import { Code, filePathToCodeLanguage } from '~/components/lib/Code';
import { Dialog } from '~/components/lib/Dialog';
import { Flex } from '~/components/lib/Flex';
import { Form } from '~/components/lib/Form';
import { IframeWithBlob } from '~/components/lib/IframeWithBlob';
import { InputTextarea } from '~/components/lib/InputTextarea';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { Messages } from '~/components/Messages';
import { SignInPrompt } from '~/components/SignInPrompt';
import { ThreadsSidebar } from '~/components/ThreadsSidebar';
import { env } from '~/env';
import { useAgentRequestsWithIframe } from '~/hooks/agent-iframe-requests';
import {
  useCurrentEntry,
  useCurrentEntryEnvironmentVariables,
} from '~/hooks/entries';
import { useQueryParams } from '~/hooks/url';
import { type chatWithAgentModel, type threadMessageModel } from '~/lib/models';
import { returnOptimisticThreadMessage } from '~/lib/thread';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';
import { handleClientError } from '~/utils/error';
import { formatBytes } from '~/utils/number';

import { PlaceholderCard, PlaceholderSection } from './lib/Placeholder';

type RunView = 'conversation' | 'output' | undefined;

type Props = {
  namespace: string;
  name: string;
  version: string;
  showLoadingPlaceholder?: boolean;
};

type FormSchema = Pick<
  z.infer<typeof chatWithAgentModel>,
  'max_iterations' | 'new_message'
>;

export type AgentChatMutationInput = FormSchema &
  Partial<z.infer<typeof chatWithAgentModel>>;

export const AgentRunner = ({
  namespace,
  name,
  version,
  showLoadingPlaceholder,
}: Props) => {
  const { currentEntry, currentEntryId: agentId } = useCurrentEntry('agent', {
    namespace,
    name,
    version,
  });

  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { queryParams, updateQueryPath } = useQueryParams([
    'threadId',
    'view',
    'transactionHashes',
    'transactionRequestId',
  ]);
  const entryEnvironmentVariables = useCurrentEntryEnvironmentVariables(
    'agent',
    Object.keys(queryParams),
  );
  const threadId = queryParams.threadId ?? '';
  const utils = api.useUtils();

  const form = useForm<FormSchema>({
    defaultValues: {
      max_iterations: 1,
    },
  });

  const [htmlOutput, setHtmlOutput] = useState('');
  const [openedFileId, setOpenedFileId] = useState<string | null>(null);
  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const [threadsOpenForSmallScreens, setThreadsOpenForSmallScreens] =
    useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const threadQuery = api.hub.thread.useQuery(
    {
      threadId,
    },
    {
      enabled: false,
    },
  );
  const thread = threadQuery.data;

  const openedFile = openedFileId
    ? thread?.files?.find((file) => file.id === openedFileId)
    : undefined;

  const latestAssistantMessages: z.infer<typeof threadMessageModel>[] = [];
  if (thread) {
    for (let i = thread.messages.length - 1; i >= 0; i--) {
      const message = thread.messages[i]!;
      const messageType = message.metadata?.message_type ?? '';
      if (message.role === 'assistant' && !messageType.startsWith('system:')) {
        latestAssistantMessages.push(message);
      } else {
        break;
      }
    }
  }

  const _chatMutation = api.hub.chatWithAgent.useMutation();
  const chatMutation = useMutation({
    mutationFn: async (data: AgentChatMutationInput) => {
      try {
        const updatedThread = await _chatMutation.mutateAsync({
          thread_id: threadId || undefined,
          agent_id: agentId,
          agent_env_vars: entryEnvironmentVariables.metadataVariablesByKey,
          user_env_vars: entryEnvironmentVariables.urlVariablesByKey,
          ...data,
        });

        utils.hub.thread.setData(
          {
            threadId,
          },
          updatedThread,
        );

        updateQueryPath({ threadId: updatedThread.id }, 'replace', false);

        void utils.hub.threads.invalidate();
      } catch (error) {
        handleClientError({ error, title: 'Failed to run agent' });
      }
    },
  });

  const {
    agentRequestsNeedingPermissions,
    setAgentRequestsNeedingPermissions,
    conditionallyProcessAgentRequests,
    iframePostMessage,
    onIframePostMessage,
  } = useAgentRequestsWithIframe(currentEntry, chatMutation, threadId);

  const isLoading = threadQuery.isLoading && !chatMutation.isPending;

  const [__view, __setView] = useState<RunView>();
  const view = (queryParams.view as RunView) ?? __view;
  const setView = useCallback(
    (value: RunView, updateUrl = false) => {
      __setView(value);

      if (updateUrl) {
        updateQueryPath(
          {
            view: value,
          },
          'replace',
          false,
        );
      }
    },
    [updateQueryPath],
  );

  const onSubmit: SubmitHandler<FormSchema> = async (data) => {
    if (!data.new_message.trim()) return;

    utils.hub.thread.setData(
      {
        threadId,
      },
      {
        id: threadId,
        files: thread?.files ?? [],
        messages: [
          ...(thread?.messages ?? []),
          returnOptimisticThreadMessage(threadId, data.new_message),
        ],
      },
    );

    form.setValue('new_message', '');

    await chatMutation.mutateAsync(data);
  };

  const onKeyDownContent: KeyboardEventHandler<HTMLTextAreaElement> = (
    event,
  ) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  const startNewThread = () => {
    updateQueryPath({ threadId: undefined });
    form.setValue('new_message', '');
    form.setFocus('new_message');
  };

  useEffect(() => {
    if (threadId && thread?.id !== threadId) {
      void threadQuery.refetch({ cancelRefetch: true });
    }
  }, [thread, threadId, threadQuery]);

  useEffect(() => {
    const files = threadQuery?.data?.files;
    const htmlFile = files?.find((file) => file.filename === 'index.html');

    if (htmlFile) {
      const htmlContent = htmlFile.content.replaceAll(
        '{{%agent_id%}}',
        agentId,
      );
      setHtmlOutput(htmlContent);
      setView('output');
    } else {
      setHtmlOutput('');
      setView('conversation');
    }
  }, [threadQuery, htmlOutput, agentId, setView]);

  useEffect(() => {
    if (!threadId) {
      utils.hub.thread.setData(
        {
          threadId: '',
        },
        {
          files: [],
          messages: [],
          id: '',
        },
      );
    }
  }, [threadId, utils]);

  useEffect(() => {
    if (currentEntry && isAuthenticated) {
      form.setFocus('new_message');
    }
  }, [threadId, currentEntry, isAuthenticated, form]);

  useEffect(() => {
    form.reset();
  }, [agentId, form]);

  useEffect(() => {
    if (currentEntry && !form.formState.isDirty) {
      const maxIterations =
        currentEntry.details.agent?.defaults?.max_iterations ?? 1;
      form.setValue('max_iterations', maxIterations);
    }
  }, [currentEntry, form]);

  useEffect(() => {
    setThreadsOpenForSmallScreens(false);
  }, [threadId]);

  useEffect(() => {
    const agentDetails = currentEntry?.details.agent;
    const initialUserMessage = agentDetails?.initial_user_message;
    const maxIterations = agentDetails?.defaults?.max_iterations ?? 1;

    if (initialUserMessage && !threadId && !chatMutation.isPending) {
      void chatMutation.mutateAsync({
        max_iterations: maxIterations,
        new_message: initialUserMessage,
      });
    }
  }, [currentEntry, threadId, chatMutation]);

  if (!currentEntry) {
    if (showLoadingPlaceholder) return <PlaceholderSection />;
    return null;
  }

  return (
    <Form stretch onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
      <Sidebar.Root>
        <ThreadsSidebar
          onRequestNewThread={startNewThread}
          openForSmallScreens={threadsOpenForSmallScreens}
          setOpenForSmallScreens={setThreadsOpenForSmallScreens}
        />

        <Sidebar.Main>
          {isLoading ? (
            <PlaceholderCard style={{ marginTop: 'auto' }} />
          ) : (
            <>
              {view === 'output' ? (
                <>
                  <IframeWithBlob
                    html={htmlOutput}
                    minHeight={currentEntry.details.agent?.html_minimum_height}
                    onPostMessage={onIframePostMessage}
                    postMessage={iframePostMessage}
                  />

                  {latestAssistantMessages.length > 0 && (
                    <Messages
                      grow={false}
                      messages={latestAssistantMessages}
                      threadId={threadId}
                    />
                  )}
                </>
              ) : (
                <Messages
                  messages={thread?.messages ?? []}
                  threadId={threadId}
                  welcomeMessage={
                    <AgentWelcome details={currentEntry.details} />
                  }
                />
              )}
            </>
          )}

          <Sidebar.MainStickyFooter>
            <Flex direction="column" gap="m">
              <InputTextarea
                placeholder="Write your message and press enter..."
                onKeyDown={onKeyDownContent}
                disabled={!isAuthenticated}
                {...form.register('new_message')}
              />

              {isAuthenticated ? (
                <Flex align="start" gap="m">
                  <Text size="text-xs" style={{ marginRight: 'auto' }}>
                    <b>Shift + Enter</b> to add a new line
                  </Text>

                  <Flex align="start" gap="xs">
                    <BreakpointDisplay show="sidebar-small-screen">
                      <Button
                        label="Select Thread"
                        icon={<List />}
                        size="small"
                        fill="ghost"
                        onClick={() => setThreadsOpenForSmallScreens(true)}
                      />
                    </BreakpointDisplay>

                    <BreakpointDisplay show="sidebar-small-screen">
                      <Button
                        label="Edit Parameters"
                        icon={<Gear />}
                        size="small"
                        fill="ghost"
                        onClick={() => setParametersOpenForSmallScreens(true)}
                      />
                    </BreakpointDisplay>
                  </Flex>

                  {htmlOutput && (
                    <>
                      {view === 'output' ? (
                        <Tooltip asChild content="Switch to conversation view">
                          <Button
                            label="Toggle View"
                            icon={<Chats />}
                            size="small"
                            variant="secondary"
                            onClick={() => setView('conversation', true)}
                          />
                        </Tooltip>
                      ) : (
                        <Tooltip asChild content="Switch to output view">
                          <Button
                            label="Toggle View"
                            icon={<Eye />}
                            size="small"
                            variant="secondary"
                            onClick={() => setView('output', true)}
                          />
                        </Tooltip>
                      )}
                    </>
                  )}

                  <Button
                    label="Send Message"
                    type="submit"
                    icon={<ArrowRight weight="bold" />}
                    size="small"
                    loading={chatMutation.isPending}
                  />
                </Flex>
              ) : (
                <SignInPrompt />
              )}
            </Flex>
          </Sidebar.MainStickyFooter>
        </Sidebar.Main>

        <Sidebar.Sidebar
          openForSmallScreens={parametersOpenForSmallScreens}
          setOpenForSmallScreens={setParametersOpenForSmallScreens}
        >
          <Flex direction="column" gap="l">
            <Flex direction="column" gap="m">
              <Text size="text-xs" weight={600} uppercase>
                Output
              </Text>

              {thread?.files && Object.keys(thread.files).length ? (
                <CardList>
                  {Object.values(thread.files).map((file) => (
                    <Card
                      padding="s"
                      gap="s"
                      key={file.id}
                      background="sand-2"
                      onClick={() => {
                        setOpenedFileId(file.id);
                      }}
                    >
                      <Flex align="center" gap="s">
                        <Text
                          size="text-s"
                          color="violet-11"
                          clickableHighlight
                          weight={500}
                          clampLines={1}
                          style={{ marginRight: 'auto' }}
                        >
                          {file.filename}
                        </Text>

                        <Text size="text-xs">{formatBytes(file.bytes)}</Text>
                      </Flex>
                    </Card>
                  ))}
                </CardList>
              ) : (
                <Text size="text-s" color="sand-10">
                  No files generated yet.
                </Text>
              )}
            </Flex>

            {!env.NEXT_PUBLIC_CONSUMER_MODE && (
              <>
                <EntryEnvironmentVariables
                  entry={currentEntry}
                  variables={entryEnvironmentVariables}
                />

                <Flex direction="column" gap="m">
                  <Text size="text-xs" weight={600} uppercase>
                    Parameters
                  </Text>

                  <Controller
                    control={form.control}
                    name="max_iterations"
                    render={({ field }) => (
                      <Slider
                        label="Max Iterations"
                        max={20}
                        min={1}
                        step={1}
                        assistive="The maximum number of iterations to run the agent for, usually 1. Each iteration will loop back through your agent allowing it to act and reflect on LLM results."
                        {...field}
                      />
                    )}
                  />
                </Flex>
              </>
            )}
          </Flex>
        </Sidebar.Sidebar>
      </Sidebar.Root>

      <AgentPermissionsModal
        agent={currentEntry}
        onAllow={(requests) =>
          conditionallyProcessAgentRequests(requests, true)
        }
        requests={agentRequestsNeedingPermissions}
        clearRequests={() => setAgentRequestsNeedingPermissions(null)}
      />

      <Dialog.Root
        open={openedFileId !== null}
        onOpenChange={() => setOpenedFileId(null)}
      >
        <Dialog.Content
          title={openedFileId}
          size="l"
          header={
            <Button
              label="Copy file to clipboard"
              icon={<Copy />}
              size="small"
              fill="outline"
              onClick={() =>
                openedFile && copyTextToClipboard(openedFile?.content)
              }
              style={{ marginLeft: 'auto' }}
            />
          }
        >
          <Code
            bleed
            source={openedFile?.content}
            language={filePathToCodeLanguage(openedFile?.filename)}
          />
        </Dialog.Content>
      </Dialog.Root>
    </Form>
  );
};
