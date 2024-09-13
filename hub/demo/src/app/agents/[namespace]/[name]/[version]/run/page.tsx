'use client';

import { ArrowRight, ChatCircleText, Copy, Gear } from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import { type KeyboardEventHandler, useEffect, useRef, useState } from 'react';
import { Controller } from 'react-hook-form';
import { type z } from 'zod';

import { AgentWelcome } from '~/components/AgentWelcome';
import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Card, CardList } from '~/components/lib/Card';
import { Code, filePathToCodeLanguage } from '~/components/lib/Code';
import { Dialog } from '~/components/lib/Dialog';
import { Flex } from '~/components/lib/Flex';
import { Form } from '~/components/lib/Form';
import { HR } from '~/components/lib/HorizontalRule';
import { InputTextarea } from '~/components/lib/InputTextarea';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { Text } from '~/components/lib/Text';
import { Messages } from '~/components/Messages';
import { SignInPrompt } from '~/components/SignInPrompt';
import { ThreadsSidebar } from '~/components/ThreadsSidebar';
import { useZodForm } from '~/hooks/form';
import { useCurrentResource, useResourceParams } from '~/hooks/resources';
import { useThreads } from '~/hooks/threads';
import { useQueryParams } from '~/hooks/url';
import { chatWithAgentModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';
import { handleClientError } from '~/utils/error';
import { formatBytes } from '~/utils/number';
import { getQueryParams } from '~/utils/url';

export default function RunAgentPage() {
  const router = useRouter();
  const { currentResource } = useCurrentResource('agent');
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { namespace, name, version } = useResourceParams();
  const { queryParams, createQueryPath } = useQueryParams(['environmentId']);
  const environmentId = queryParams.environmentId ?? '';
  const chatMutation = api.hub.chatWithAgent.useMutation();
  const { threadsQuery } = useThreads();
  const utils = api.useUtils();
  const agentId = `${namespace}/${name}/${version}`;

  const form = useZodForm(chatWithAgentModel, {
    defaultValues: { agent_id: agentId },
  });

  const [openedFileName, setOpenedFileName] = useState<string | null>(null);
  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const [threadsOpenForSmallScreens, setThreadsOpenForSmallScreens] =
    useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const environmentQuery = api.hub.environment.useQuery(
    {
      environmentId,
    },
    {
      enabled: false,
    },
  );

  const environment = environmentQuery.data;
  const openedFile = openedFileName
    ? environment?.files?.[openedFileName]
    : undefined;

  async function onSubmit(values: z.infer<typeof chatWithAgentModel>) {
    try {
      if (!values.new_message.trim()) return;

      if (environmentId) {
        values.environment_id = environmentId;
      }

      utils.hub.environment.setData(
        {
          environmentId,
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
        },
      );

      form.setValue('new_message', '');

      values.user_env_vars = getQueryParams();
      if (currentResource?.details.env_vars) {
        values.agent_env_vars = {
          ...(values.agent_env_vars ?? {}),
          [values.agent_id]: currentResource?.details?.env_vars ?? {},
        };
      }

      const response = await chatMutation.mutateAsync(values);

      utils.hub.environment.setData(
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
    utils.hub.environment.setData(
      {
        environmentId: '',
      },
      {
        conversation: [],
        environmentId: '',
        files: {},
      },
    );

    router.replace(createQueryPath({ environmentId: undefined }));

    form.setValue('new_message', '');
    form.setFocus('new_message');
  };

  useEffect(() => {
    if (environmentId && environmentId !== environment?.environmentId) {
      void environmentQuery.refetch();
    }
  }, [environment, environmentId, environmentQuery]);

  useEffect(() => {
    if (currentResource && isAuthenticated) {
      form.setFocus('new_message');
    }
  }, [environmentId, currentResource, isAuthenticated, form]);

  useEffect(() => {
    setThreadsOpenForSmallScreens(false);
  }, [environmentId]);

  if (!currentResource) return null;

  return (
    <Form stretch onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
      <Sidebar.Root>
        <ThreadsSidebar
          onRequestNewThread={startNewThread}
          openForSmallScreens={threadsOpenForSmallScreens}
          setOpenForSmallScreens={setThreadsOpenForSmallScreens}
        />

        <Sidebar.Main>
          <Messages
            loading={environmentQuery.isLoading}
            messages={environment?.conversation ?? []}
            threadId={agentId}
            welcomeMessage={<AgentWelcome details={currentResource.details} />}
          />

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

                  <BreakpointDisplay show="sidebar-small-screen">
                    <Button
                      label="Select Thread"
                      icon={<ChatCircleText />}
                      size="small"
                      fill="outline"
                      onClick={() => setThreadsOpenForSmallScreens(true)}
                    />
                  </BreakpointDisplay>

                  <BreakpointDisplay show="sidebar-small-screen">
                    <Button
                      label="Edit Parameters"
                      icon={<Gear />}
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
          </Sidebar.MainStickyFooter>
        </Sidebar.Main>

        <Sidebar.Sidebar
          openForSmallScreens={parametersOpenForSmallScreens}
          setOpenForSmallScreens={setParametersOpenForSmallScreens}
        >
          <Text size="text-xs" weight={500} uppercase>
            Output
          </Text>

          {environment?.files && Object.keys(environment.files).length ? (
            <CardList>
              {Object.values(environment.files).map((file) => (
                <Card
                  padding="s"
                  gap="s"
                  key={file.name}
                  background="sand-2"
                  onClick={() => {
                    setOpenedFileName(file.name);
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
                      {file.name}
                    </Text>

                    <Text size="text-xs">{formatBytes(file.size)}</Text>
                  </Flex>
                </Card>
              ))}
            </CardList>
          ) : (
            <Text size="text-s" color="sand-10">
              No files generated yet.
            </Text>
          )}

          <HR />

          <Text size="text-xs" weight={500} uppercase>
            Parameters
          </Text>

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
            language={filePathToCodeLanguage(openedFileName)}
          />
        </Dialog.Content>
      </Dialog.Root>
    </Form>
  );
}
