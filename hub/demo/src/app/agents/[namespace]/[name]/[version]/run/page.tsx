'use client';

// TODO: Adding new message to existing thread isn't working as expected
// TODO: More testing and polish
// TODO: Small screens for history sidebar
// TODO: Display text if user has no threads yet - eg: Your threads will appear here...

import {
  ArrowRight,
  Copy,
  Gear,
  Info,
  Plus,
  ShareFat,
} from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import {
  type KeyboardEventHandler,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Controller } from 'react-hook-form';
import { type z } from 'zod';

import { AgentWelcome } from '~/components/AgentWelcome';
import { ChatThread } from '~/components/inference/ChatThread';
import { Badge } from '~/components/lib/Badge';
import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Card, CardList } from '~/components/lib/Card';
import { Code, filePathToCodeLanguage } from '~/components/lib/Code';
import { Dialog } from '~/components/lib/Dialog';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { Form } from '~/components/lib/Form';
import { HR } from '~/components/lib/HorizontalRule';
import { InputTextarea } from '~/components/lib/InputTextarea';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Text } from '~/components/lib/Text';
import { Timestamp } from '~/components/lib/Timestamp';
import { Tooltip } from '~/components/lib/Tooltip';
import { SignInPrompt } from '~/components/SignInPrompt';
import { useZodForm } from '~/hooks/form';
import { useAgentChatHistory } from '~/hooks/history';
import { useCurrentResource, useResourceParams } from '~/hooks/resources';
import { useQueryParams } from '~/hooks/url';
import { agentRequestModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';
import { handleClientError } from '~/utils/error';
import { formatBytes } from '~/utils/number';

export default function RunAgentPage() {
  const router = useRouter();
  const { currentResource } = useCurrentResource('agent');
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { namespace, name, version } = useResourceParams();
  const { queryParams, createQueryPath } = useQueryParams(['environmentId']);
  const chatMutation = api.hub.agentChat.useMutation();
  const { threads, threadsQuery } = useAgentChatHistory();
  const utils = api.useUtils();

  const form = useZodForm(agentRequestModel, {
    defaultValues: { agent_id: `${namespace}/${name}/${version}` },
  });

  const [openedFileName, setOpenedFileName] = useState<string | null>(null);
  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  // const [historyOpenForSmallScreens, setHistoryOpenForSmallScreens] =
  //   useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const environmentQuery = api.hub.loadEnvironment.useQuery(
    {
      environmentId: queryParams.environmentId!,
    },
    {
      enabled: false,
    },
  );

  const environment = environmentQuery.data;
  const openedFile = openedFileName && environment?.files?.[openedFileName];

  const shareLink = useMemo(() => {
    if (queryParams.environmentId) {
      const urlEncodedEnv = encodeURIComponent(queryParams.environmentId);
      return `${window.location.origin}/agents/${namespace}/${name}/${version}/run?queryParams.environmentId=${urlEncodedEnv}`;
    }
  }, [queryParams.environmentId, namespace, name, version]);

  function getUrlParams() {
    const searchParams = new URLSearchParams(window.location.search);
    const params: Record<string, string> = {};

    searchParams.forEach((value, key) => {
      params[key] = value;
    });

    return params;
  }

  async function onSubmit(values: z.infer<typeof agentRequestModel>) {
    try {
      if (!values.new_message.trim()) return;

      if (queryParams.environmentId) {
        values.environment_id = queryParams.environmentId;
      }

      utils.hub.loadEnvironment.setData(
        {
          environmentId: queryParams.environmentId ?? '',
        },
        {
          conversation: [
            ...(environment?.conversation ?? []),
            {
              content: values.new_message,
              role: 'user',
            },
          ],
          environmentId: environment?.environmentId ?? '',
          files: environment?.files ?? {},
          fileStructure: environment?.fileStructure ?? [],
        },
      );

      form.setValue('new_message', '');
      form.setFocus('new_message');

      values.user_env_vars = getUrlParams();
      if (currentResource?.details.env_vars) {
        values.agent_env_vars = {
          ...(values.agent_env_vars ?? {}),
          [values.agent_id]: currentResource?.details?.env_vars ?? {},
        };
      }

      const response = await chatMutation.mutateAsync(values);

      utils.hub.loadEnvironment.setData(
        {
          environmentId: response.environmentId,
        },
        response,
      );

      router.replace(
        createQueryPath({ environmentId: response.environmentId }),
      );

      void threadsQuery.refetch();
    } catch (error) {
      handleClientError({ error, title: 'Failed to communicate with agent' });
    }
  }

  const onKeyDownContent: KeyboardEventHandler<HTMLTextAreaElement> = (
    event,
  ) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  const startNewThread = () => {
    utils.hub.loadEnvironment.setData(
      {
        environmentId: '',
      },
      {
        conversation: [],
        environmentId: '',
        files: {},
        fileStructure: [],
      },
    );

    router.replace(createQueryPath({ environmentId: undefined }));

    form.setValue('new_message', '');
    form.setFocus('new_message');
  };

  useEffect(() => {
    if (
      queryParams.environmentId &&
      queryParams.environmentId !== environment?.environmentId
    ) {
      void environmentQuery.refetch();
    }
  }, [environment, queryParams.environmentId, environmentQuery]);

  useEffect(() => {
    if (isAuthenticated) {
      form.setFocus('new_message');
    }
  }, [isAuthenticated, form]);

  if (!currentResource) return null;

  return (
    <Form stretch onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={parametersOpenForSmallScreens}
          setOpenForSmallScreens={setParametersOpenForSmallScreens}
        >
          <Text size="text-l">Threads</Text>

          <CardList>
            <Card
              padding="s"
              onClick={startNewThread}
              background={!queryParams.environmentId ? 'sand-0' : 'sand-2'}
            >
              <Flex align="center" gap="s">
                <SvgIcon
                  icon={<Plus weight="bold" />}
                  color="green-10"
                  size="xs"
                />
                <Text size="text-xs" weight={500} color="sand-12">
                  New Thread
                </Text>
              </Flex>
            </Card>

            {threads.map((thread) => (
              <Card
                href={thread.url}
                padding="s"
                gap="xs"
                background={
                  queryParams.environmentId === thread.environmentId
                    ? 'sand-0'
                    : 'sand-2'
                }
                key={thread.environmentId}
              >
                <Text as="span" size="text-xs" weight={500} color="sand-12">
                  {thread.description}
                </Text>

                <Flex align="center" gap="s">
                  <Text size="text-xs" style={{ marginRight: 'auto' }}>
                    <Timestamp date={thread.lastMessageAt} />
                  </Text>

                  <Tooltip
                    asChild
                    content={`${thread.messageCount} message prompt${thread.messageCount !== 1 ? 's' : ''}`}
                    key={thread.environmentId}
                  >
                    <Badge
                      label={thread.messageCount}
                      count
                      variant="neutral"
                      size="small"
                    />
                  </Tooltip>
                </Flex>
              </Card>
            ))}
          </CardList>
        </Sidebar.Sidebar>

        <Sidebar.Main>
          <ChatThread
            loading={environmentQuery.isLoading}
            messages={environment?.conversation ?? []}
            welcomeMessage={<AgentWelcome details={currentResource.details} />}
          />

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

                <BreakpointDisplay show="sidebar-small-screen">
                  <Button
                    label="Edit Parameters"
                    icon={<Gear weight="bold" />}
                    size="small"
                    fill="outline"
                    onClick={() => setParametersOpenForSmallScreens(true)}
                  />
                </BreakpointDisplay>

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
        </Sidebar.Main>

        <Sidebar.Sidebar
          openForSmallScreens={parametersOpenForSmallScreens}
          setOpenForSmallScreens={setParametersOpenForSmallScreens}
        >
          <Flex align="center" gap="m">
            <Text size="text-l">Output</Text>

            <Dropdown.Root>
              <Dropdown.Trigger asChild>
                <Button
                  label="Output Info"
                  icon={<Info weight="duotone" />}
                  size="small"
                  fill="ghost"
                />
              </Dropdown.Trigger>

              <Dropdown.Content style={{ maxWidth: '30rem' }}>
                <Dropdown.Section>
                  <Dropdown.SectionContent>
                    <Flex direction="column" gap="s">
                      <Flex align="center" gap="m">
                        <Text size="text-xs" weight={600}>
                          Environment
                        </Text>

                        <Button
                          label="Share"
                          icon={<ShareFat />}
                          size="small"
                          fill="ghost"
                          onClick={() =>
                            shareLink && copyTextToClipboard(shareLink)
                          }
                          style={{ marginLeft: 'auto' }}
                          disabled={!queryParams.environmentId}
                        />
                      </Flex>

                      <Text size="text-xs">
                        {queryParams.environmentId ??
                          'No output environment has been generated yet.'}
                      </Text>
                    </Flex>
                  </Dropdown.SectionContent>
                </Dropdown.Section>
              </Dropdown.Content>
            </Dropdown.Root>
          </Flex>

          {environment?.fileStructure.length ? (
            <CardList>
              {environment.fileStructure.map((fileInfo) => (
                <Card
                  padding="s"
                  gap="s"
                  key={fileInfo.name}
                  onClick={() => {
                    setOpenedFileName(fileInfo.name);
                  }}
                >
                  <Flex align="center" gap="s">
                    <Text
                      size="text-s"
                      color="violet-11"
                      weight={500}
                      clampLines={1}
                      style={{ marginRight: 'auto' }}
                    >
                      {fileInfo.name}
                    </Text>

                    <Text size="text-xs">{formatBytes(fileInfo.size)}</Text>
                  </Flex>
                </Card>
              ))}
            </CardList>
          ) : (
            <Text size="text-s">No files have been generated yet.</Text>
          )}

          <HR />

          <Text size="text-l">Parameters</Text>

          <Controller
            control={form.control}
            defaultValue={1}
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
        </Sidebar.Sidebar>
      </Sidebar.Root>

      <Dialog.Root
        open={openedFileName !== null}
        onOpenChange={() => setOpenedFileName(null)}
      >
        <Dialog.Content
          title={openedFileName}
          size="l"
          header={
            <Button
              label="Copy file to clipboard"
              icon={<Copy />}
              size="small"
              fill="outline"
              onClick={() => openedFile && copyTextToClipboard(openedFile)}
              style={{ marginLeft: 'auto' }}
            />
          }
        >
          <Code
            bleed
            source={openedFile}
            language={filePathToCodeLanguage(openedFileName)}
          />
        </Dialog.Content>
      </Dialog.Root>
    </Form>
  );
}
