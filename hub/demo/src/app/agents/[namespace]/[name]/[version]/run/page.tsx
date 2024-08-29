'use client';

import { ArrowRight, Copy, Gear, Info, ShareFat } from '@phosphor-icons/react';
import {
  type KeyboardEventHandler,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Controller } from 'react-hook-form';
import { type z } from 'zod';

import { ChatThread } from '~/components/inference/ChatThread';
import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Card } from '~/components/lib/Card';
import { Dialog } from '~/components/lib/Dialog';
import { Dropdown } from '~/components/lib/Dropdown';
import { Flex } from '~/components/lib/Flex';
import { Form } from '~/components/lib/Form';
import { HR } from '~/components/lib/HorizontalRule';
import { InputTextarea } from '~/components/lib/InputTextarea';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { Text } from '~/components/lib/Text';
import { SignInPrompt } from '~/components/SignInPrompt';
import { useZodForm } from '~/hooks/form';
import { useResourceParams } from '~/hooks/resources';
import {
  agentRequestModel,
  chatCompletionsModel,
  type messageModel,
} from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';
import { handleClientError } from '~/utils/error';
import { formatBytes } from '~/utils/number';
import { useSearchParams } from 'next/dist/client/components/navigation';
import { FileStructure } from '~/server/api/routers/hub';

const LOCAL_STORAGE_KEY = 'agent_inference_conversation';

export default function RunAgentPage() {
  const { namespace, name, version } = useResourceParams();
  const searchParams = useSearchParams();
  const environmentId = searchParams.get('environmentId');
  const formRef = useRef<HTMLFormElement | null>(null);
  const form = useZodForm(agentRequestModel, {
    defaultValues: { agent_id: `${namespace}/${name}/${version}` },
  });
  const environmentQuery = environmentId
    ? api.hub.loadEnvironment.useQuery({
        environmentId: environmentId as string,
      })
    : null;
  const chatMutation = api.hub.agentChat.useMutation();
  const [environmentName, setPreviousEnvironmentName] = useState<string>('');
  const [conversation, setConversation] = useState<
    z.infer<typeof messageModel>[]
  >([]);
  const [fileStructure, setFileStructure] = useState<FileStructure[]>([]);
  const [files, setFiles] = useState<Record<string, string>>({});
  const [openedFileName, setOpenedFileName] = useState<string | null>(null);
  const store = useAuthStore();
  const isAuthenticated = store.isAuthenticated();

  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const openedFile = openedFileName && files && files[openedFileName];

  const shareLink = useMemo(() => {
    if (environmentName && namespace && name && version) {
      const urlEncodedEnv = encodeURIComponent(environmentName);
      return `${window.location.origin}/agents/${namespace}/${name}/${version}/run?environmentId=${urlEncodedEnv}`;
    }
  }, [environmentName, namespace, name, version]);

  useEffect(() => {
    const response = environmentQuery?.data;
    if (response && !environmentName) {
      setPreviousEnvironmentName(() => response.environmentId);

      chatMutation.trpc.path;

      setFileStructure(() => response.fileStructure);
      setFiles(() => response.files);
      setConversation(() => response.conversation);
    }
  }, [environmentQuery]);

  async function onSubmit(values: z.infer<typeof agentRequestModel>) {
    if (environmentName) {
      values.environment_id = environmentName;
    }

    try {
      const response = await chatMutation.mutateAsync(values);
      setPreviousEnvironmentName(() => response.environmentId);
      setFileStructure(() => response.fileStructure);
      setFiles(() => response.files);
      setConversation(response.conversation);

      form.setValue('new_message', '');
      form.setFocus('new_message');
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
    localStorage.removeItem(LOCAL_STORAGE_KEY);
    setConversation([]);
  };

  useEffect(() => {
    const currConv = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (currConv) {
      try {
        const conv: unknown = JSON.parse(currConv);
        const parsed = chatCompletionsModel.parse(conv);
        setConversation(parsed.messages);
      } catch (error) {
        console.error(error);
        clearConversation();
      }
    }
  }, [setConversation]);

  useEffect(() => {
    if (isAuthenticated) {
      form.setFocus('new_message');
    }
  }, [isAuthenticated, form]);

  return (
    <Form stretch onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
      <Sidebar.Root>
        <Sidebar.Main>
          {isAuthenticated ? (
            <ChatThread messages={conversation} />
          ) : (
            <SignInPrompt />
          )}

          <Flex direction="column" gap="m">
            <InputTextarea
              placeholder="Write your message and press enter..."
              onKeyDown={onKeyDownContent}
              disabled={!isAuthenticated}
              {...form.register('new_message')}
            />

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
                disabled={!isAuthenticated}
                loading={chatMutation.isPending}
              />
            </Flex>
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

          <Flex direction="column" gap="xs">
            {fileStructure.length ? (
              fileStructure.map((fileInfo) => (
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
                      color="violet8"
                      weight={500}
                      clampLines={1}
                      style={{ marginRight: 'auto' }}
                    >
                      {fileInfo.name}
                    </Text>

                    <Text size="text-xs">{formatBytes(fileInfo.size)}</Text>
                  </Flex>
                </Card>
              ))
            ) : (
              <Text size="text-s">No files have been generated yet.</Text>
            )}
          </Flex>

          <HR />

          <Text size="text-l">Parameters</Text>

          <Controller
            control={form.control}
            defaultValue={5}
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
          <Text size="text-s" color="sand12" style={{ whiteSpace: 'pre-wrap' }}>
            {openedFile}
          </Text>
        </Dialog.Content>
      </Dialog.Root>
    </Form>
  );
}
