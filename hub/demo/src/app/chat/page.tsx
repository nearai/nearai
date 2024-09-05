'use client';

import { ArrowRight, Gear } from '@phosphor-icons/react';
import {
  type KeyboardEventHandler,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Controller, type SubmitHandler } from 'react-hook-form';
import { type z } from 'zod';

import { ChatThread } from '~/components/inference/ChatThread';
import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Combobox, type ComboboxItem } from '~/components/lib/Combobox';
import { Flex } from '~/components/lib/Flex';
import { Form } from '~/components/lib/Form';
import { InputTextarea } from '~/components/lib/InputTextarea';
import { Sidebar } from '~/components/lib/Sidebar';
import { Slider } from '~/components/lib/Slider';
import { Text } from '~/components/lib/Text';
import { SignInPrompt } from '~/components/SignInPrompt';
import { useZodForm } from '~/hooks/form';
import { useListModels } from '~/hooks/queries';
import { chatCompletionsModel, type messageModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { handleClientError } from '~/utils/error';

const LOCAL_STORAGE_KEY = 'inference_conversation';

const roles: ComboboxItem[] = [
  { label: 'User', value: 'user' },
  { label: 'Assistant', value: 'assistant' },
  { label: 'System', value: 'system' },
];

const providers: ComboboxItem[] = [
  { label: 'Fireworks', value: 'fireworks' },
  { label: 'Hyperbolic', value: 'hyperbolic' },
];

export default function InferencePage() {
  const formRef = useRef<HTMLFormElement | null>(null);
  const form = useZodForm(chatCompletionsModel);
  const chatMutation = api.hub.chat.useMutation();
  const provider = form.watch('provider');
  const listModels = useListModels(provider);
  const [conversation, setConversation] = useState<
    z.infer<typeof messageModel>[]
  >([]);
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);

  const [parametersOpenForSmallScreens, setParametersOpenForSmallScreens] =
    useState(false);

  const models: ComboboxItem[] = useMemo(
    () =>
      listModels.data?.map((model) => ({
        ...model,
        label: model.label.split('/').pop(),
      })) ?? [],
    [listModels.data],
  );

  const onSubmit: SubmitHandler<z.infer<typeof chatCompletionsModel>> = async (
    values,
  ) => {
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
    if (!provider || !models.length) return;

    const currentModel = form.getValues('model');
    const matchingModel = models.find((m) => m.value === currentModel);

    if (!matchingModel) {
      form.setValue('model', (models[0]?.value ?? '').toString());
    }
  }, [form, provider, models]);

  useEffect(() => {
    const previousConversationRaw = localStorage.getItem(LOCAL_STORAGE_KEY);

    if (previousConversationRaw) {
      try {
        const parsed = chatCompletionsModel.parse(
          JSON.parse(previousConversationRaw),
        );
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
        <Sidebar.Main>
          <ChatThread messages={conversation} />

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
          <Text size="text-l">Parameters</Text>

          <Controller
            control={form.control}
            defaultValue="fireworks"
            name="provider"
            render={({ field }) => (
              <Combobox label="Provider" items={providers} {...field} />
            )}
          />

          <Controller
            control={form.control}
            defaultValue="fireworks::accounts/fireworks/models/mixtral-8x22b-instruct"
            name="model"
            render={({ field }) => (
              <Combobox label="Model" items={models} {...field} />
            )}
          />

          <Controller
            control={form.control}
            defaultValue="user"
            name="messages.0.role"
            render={({ field }) => (
              <Combobox label="Role" items={roles} {...field} />
            )}
          />

          <Controller
            control={form.control}
            defaultValue={0.1}
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
