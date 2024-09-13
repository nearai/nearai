'use client';

import { ArrowRight, ChatCircleText, Gear } from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import {
  type KeyboardEventHandler,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Controller, type SubmitHandler } from 'react-hook-form';
import { type z } from 'zod';

import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Combobox, type ComboboxOption } from '~/components/lib/Combobox';
import { Flex } from '~/components/lib/Flex';
import { Form } from '~/components/lib/Form';
import { InputTextarea } from '~/components/lib/InputTextarea';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { Text } from '~/components/lib/Text';
import { Messages } from '~/components/Messages';
import { SignInPrompt } from '~/components/SignInPrompt';
import { ThreadsSidebar } from '~/components/ThreadsSidebar';
import { useZodForm } from '~/hooks/form';
import { useListModels } from '~/hooks/queries';
import { chatModel, type messageModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { handleClientError } from '~/utils/error';

const LOCAL_STORAGE_KEY = 'inference_conversation';

const roleOptions: ComboboxOption[] = [
  { label: 'User', value: 'user' },
  { label: 'Assistant', value: 'assistant' },
  { label: 'System', value: 'system' },
];

const providerOptions: ComboboxOption[] = [
  { label: 'Fireworks', value: 'fireworks' },
  { label: 'Hyperbolic', value: 'hyperbolic' },
];

export default function InferencePage() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement | null>(null);
  const form = useZodForm(chatModel);
  const chatMutation = api.hub.chat.useMutation();
  const provider = form.watch('provider');
  const models = useListModels(provider);
  const [conversation, setConversation] = useState<
    z.infer<typeof messageModel>[]
  >([]);
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);

  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);
  const [threadsOpenForSmallScreens, setThreadsOpenForSmallScreens] =
    useState(false);

  const modelOptions: ComboboxOption[] = useMemo(
    () =>
      models.data?.map((model) => ({
        ...model,
        label: model.label.split('/').pop(),
      })) ?? [],
    [models.data],
  );

  const onSubmit: SubmitHandler<z.infer<typeof chatModel>> = async (values) => {
    try {
      const message = values.messages.at(-1)!;
      if (!message.content.trim()) return;

      values.messages = [...conversation, ...values.messages];
      values.stop = ['[INST]'];

      setConversation((current) => [
        ...current,
        {
          content: message.content,
          role: message.role,
        },
      ]);

      form.setValue('messages.0.content', '');
      form.setFocus('messages.0.content');

      const response = await chatMutation.mutateAsync(values);

      values.messages = [
        ...values.messages,
        ...response.choices.map((choice) => choice.message),
      ];

      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(values));
      setConversation(values.messages);
    } catch (error) {
      handleClientError({ error, title: 'Failed to communicate with model' });
    }
  };

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
    if (!provider || !modelOptions.length) return;

    const currentModel = form.getValues('model');
    const matchingModel = modelOptions.find((m) => m.value === currentModel);

    if (!matchingModel) {
      form.setValue('model', (modelOptions[0]?.value ?? '').toString());
    }
  }, [form, provider, modelOptions]);

  useEffect(() => {
    const previousConversationRaw = localStorage.getItem(LOCAL_STORAGE_KEY);

    if (previousConversationRaw) {
      try {
        const parsed = chatModel.parse(JSON.parse(previousConversationRaw));
        setConversation(parsed.messages);
      } catch (error) {
        console.error(error);
        clearConversation();
      }
    }
  }, [setConversation]);

  useEffect(() => {
    if (isAuthenticated) {
      form.setFocus('messages.0.content');
    }
  }, [isAuthenticated, form]);

  return (
    <Form stretch onSubmit={form.handleSubmit(onSubmit)} ref={formRef}>
      <Sidebar.Root>
        <ThreadsSidebar
          onRequestNewThread={() => router.push('/agents')}
          openForSmallScreens={threadsOpenForSmallScreens}
          setOpenForSmallScreens={setThreadsOpenForSmallScreens}
        />

        <Sidebar.Main>
          <Messages threadId="chat" messages={conversation} />

          <Sidebar.MainStickyFooter>
            <Flex direction="column" gap="m">
              <InputTextarea
                placeholder="Write your message and press enter..."
                onKeyDown={onKeyDownContent}
                disabled={!isAuthenticated}
                {...form.register('messages.0.content')}
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
          </Sidebar.MainStickyFooter>
        </Sidebar.Main>

        <Sidebar.Sidebar
          openForSmallScreens={parametersOpenForSmallScreens}
          setOpenForSmallScreens={setParametersOpenForSmallScreens}
        >
          <Text size="text-xs" weight={500} uppercase>
            Parameters
          </Text>

          <Controller
            control={form.control}
            defaultValue="fireworks"
            name="provider"
            render={({ field }) => (
              <Combobox label="Provider" items={providerOptions} {...field} />
            )}
          />

          <Controller
            control={form.control}
            defaultValue="fireworks::accounts/fireworks/models/mixtral-8x22b-instruct"
            name="model"
            render={({ field }) => (
              <Combobox label="Model" items={modelOptions} {...field} />
            )}
          />

          <Controller
            control={form.control}
            defaultValue="user"
            name="messages.0.role"
            render={({ field }) => (
              <Combobox label="Role" items={roleOptions} {...field} />
            )}
          />

          <Controller
            control={form.control}
            defaultValue={1.0}
            name="temperature"
            render={({ field }) => (
              <Slider
                label="Temperature"
                max={2}
                min={0}
                step={0.01}
                assistive="The temperature for sampling"
                {...field}
              />
            )}
          />

          <Controller
            control={form.control}
            defaultValue={128}
            name="max_tokens"
            render={({ field }) => (
              <Slider
                label="Max Tokens"
                max={2048}
                min={1}
                step={1}
                assistive="The maximum number of tokens to generate"
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
}
