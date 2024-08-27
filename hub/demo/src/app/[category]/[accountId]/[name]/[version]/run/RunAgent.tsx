'use client';

import { ArrowRight, Gear } from '@phosphor-icons/react';
import {
  type KeyboardEventHandler,
  useEffect,
  useRef,
  useState,
} from 'react';
import { Controller } from 'react-hook-form';
import { type z } from 'zod';

import { useZodForm } from '~/hooks/form';
import {
  chatCompletionsModel,
  type messageModel,
  agentRequestModel,
} from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';

import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Flex } from '~/components/lib/Flex';
import { Form } from '~/components/lib/Form';
import { InputTextarea } from '~/components/lib/InputTextarea';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { Text } from '~/components/lib/Text';
import { SignInPrompt } from '~/components/SignInPrompt';
import s from '~/components/inference/ChatInference.module.scss';
import { ChatThread } from '~/components/inference/ChatThread';
import { useParams } from 'next/navigation';
import { Card } from '~/components/lib/Card';
import { Dialog } from '~/components/lib/Dialog';

const LOCAL_STORAGE_KEY = 'agent_inference_conversation';

export const RunAgent = () => {
  const { category, accountId, name, version } = useParams();
  const formRef = useRef<HTMLFormElement | null>(null);
  const form = useZodForm(agentRequestModel, {
    defaultValues: { agent_id: `${accountId}/${name}/${version}` },
  });
  const chatMutation = api.hub.agentChat.useMutation();
  const [previousEnvironmentName, setPreviousEnvironmentName] =
    useState<string>('');
  const [conversation, setConversation] = useState<
    z.infer<typeof messageModel>[]
  >([]);
  const [openedFileName, setOpenedFileName] = useState<string | null>(null);
  const store = useAuthStore();
  const isAuthenticated = store.isAuthenticated();

  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const openedFile = openedFileName && chatMutation.data?.files[openedFileName];

  async function onSubmit(values: z.infer<typeof agentRequestModel>) {
    if (previousEnvironmentName) {
      values.environment_id = previousEnvironmentName;
    }

    const response = await chatMutation.mutateAsync(values);
    setPreviousEnvironmentName(() => response.environmentName);

    const parsedChat = response.chat;
    setConversation(parsedChat);

    form.setValue('new_message', '');
    form.setFocus('new_message');
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

  if (category !== 'agent') {
    return (
      <div>
        <h1>Only Agent is supported by this run component</h1>
      </div>
    );
  }

  return (
    <Form
      onSubmit={form.handleSubmit(onSubmit)}
      className={s.layout}
      ref={formRef}
    >
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
          <Text size="text-l">Output</Text>
          {previousEnvironmentName && (
            <Text size="text-xs">
              <b>Environment</b> {previousEnvironmentName}
            </Text>
          )}
          <Flex direction="column" gap="xs">
            {chatMutation.data ? (
              chatMutation.data.fileStructure.map((fileInfo) => (
                <Card
                  key={fileInfo.name}
                  onClick={() => {
                    console.log(fileInfo.name);
                    setOpenedFileName(fileInfo.name);
                  }}
                >
                  {fileInfo.name} {fileInfo.size} bytes
                </Card>
              ))
            ) : (
              <Text size="text-s">No files have been generated yet.</Text>
            )}
          </Flex>

          <Dialog.Root
            open={openedFileName !== null}
            onOpenChange={() => setOpenedFileName(null)}
          >
            <Dialog.Content title={openedFileName}>{openedFile}</Dialog.Content>
          </Dialog.Root>

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
    </Form>
  );
};
