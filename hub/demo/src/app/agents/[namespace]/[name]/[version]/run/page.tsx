'use client';

import { ArrowRight, Copy, Gear, Info, ShareFat } from '@phosphor-icons/react';
import { useSearchParams } from 'next/dist/client/components/navigation';
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
import { PlaceholderSection } from '~/components/lib/Placeholder';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { Text } from '~/components/lib/Text';
import { SignInPrompt } from '~/components/SignInPrompt';
import { useZodForm } from '~/hooks/form';
import { useCurrentResource, useResourceParams } from '~/hooks/resources';
import { agentRequestModel, type messageModel } from '~/lib/models';
import { type FileStructure } from '~/server/api/routers/hub';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';
import { handleClientError } from '~/utils/error';
import { formatBytes } from '~/utils/number';

export default function RunAgentPage() {
  const { currentResource } = useCurrentResource('agent');
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { namespace, name, version } = useResourceParams();
  const searchParams = useSearchParams();
  const environmentId = searchParams.get('environmentId');
  const chatMutation = api.hub.agentChat.useMutation();

  const form = useZodForm(agentRequestModel, {
    defaultValues: { agent_id: `${namespace}/${name}/${version}` },
  });

  const environmentQuery = api.hub.loadEnvironment.useQuery(
    {
      environmentId: environmentId!,
    },
    {
      enabled: !!environmentId,
    },
  );

  const [environmentName, setEnvironmentName] = useState<string>('');
  const [conversation, setConversation] = useState<
    z.infer<typeof messageModel>[]
  >([]);
  const [fileStructure, setFileStructure] = useState<FileStructure[]>([]);
  const [files, setFiles] = useState<Record<string, string>>({});
  const [openedFileName, setOpenedFileName] = useState<string | null>(null);
  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const openedFile = openedFileName && files?.[openedFileName];

  const shareLink = useMemo(() => {
    if (environmentName) {
      const urlEncodedEnv = encodeURIComponent(environmentName);
      return `${window.location.origin}/agents/${namespace}/${name}/${version}/run?environmentId=${urlEncodedEnv}`;
    }
  }, [environmentName, namespace, name, version]);

  useEffect(() => {
    const data = environmentQuery?.data;

    if (data && !environmentName) {
      setEnvironmentName(data.environmentId);

      chatMutation.trpc.path;

      setFileStructure(() => data.fileStructure);
      setFiles(() => data.files);
      setConversation(() => data.conversation);
    }
  }, [chatMutation.trpc.path, environmentName, environmentQuery.data]);

  async function onSubmit(values: z.infer<typeof agentRequestModel>) {
    try {
      if (!values.new_message.trim()) return;

      if (environmentName) {
        values.environment_id = environmentName;
      }

      setConversation((current) => [
        ...current,
        {
          content: values.new_message,
          role: 'user',
        },
      ]);

      form.setValue('new_message', '');
      form.setFocus('new_message');

      const response = await chatMutation.mutateAsync(values);
      setEnvironmentName(() => response.environmentId);
      setFileStructure(() => response.fileStructure);
      setFiles(() => response.files);
      setConversation(response.conversation);
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

  const clearConversation = () => {
    setConversation([]);
  };

  useEffect(() => {
    if (isAuthenticated) {
      form.setFocus('new_message');
    }
  }, [isAuthenticated, form]);

  if (!currentResource) return null;

  if (environmentQuery.isLoading) {
    return <PlaceholderSection />;
  }

  return (
    <Form stretch onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
      <Sidebar.Root>
        <Sidebar.Main>
          <ChatThread
            messages={conversation}
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
            <Text size="text-l" style={{ marginRight: 'auto' }}>
              Output
            </Text>

            <Dropdown.Root>
              <Dropdown.Trigger asChild>
                <Button
                  label="Output Info"
                  icon={<Info weight="duotone" />}
                  size="small"
                  fill="outline"
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
                          disabled={!environmentName}
                        />
                      </Flex>

                      <Text size="text-xs">
                        {environmentName ||
                          'No output environment has been generated yet.'}
                      </Text>
                    </Flex>
                  </Dropdown.SectionContent>
                </Dropdown.Section>
              </Dropdown.Content>
            </Dropdown.Root>
          </Flex>

          {fileStructure.length ? (
            <CardList>
              {fileStructure.map((fileInfo) => (
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
                assistive="The maximum number of iterations to run the agent for."
                {...field}
              />
            )}
          />

          <Flex direction="column" gap="m" style={{ marginTop: 'auto' }}>
            <Button
              label="Clear Conversation"
              onClick={clearConversation}
              size="small"
              variant="secondary"
            />
          </Flex>
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
