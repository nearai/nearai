'use client';

import {
  Button,
  Card,
  Dialog,
  Flex,
  Form,
  openToast,
  PlaceholderStack,
  Text,
} from '@near-pagoda/ui';
import { PencilSimple } from '@phosphor-icons/react';
import { useRef } from 'react';
import { type z } from 'zod';

import { trpc } from '~/trpc/TRPCProvider';

import {
  CURRENT_AGENT_PROTOCOL_SCHEMA,
  requestDataFormSchema,
  type requestDataSchema,
} from './schema';

type Props = {
  contentId: string;
  content: z.infer<typeof requestDataSchema>['request_data'];
};

export const RequestData = ({ content }: Props) => {
  return (
    <Card animateIn>
      <Flex direction="column" gap="m" align="start">
        <Flex direction="column" gap="s">
          {content.title && (
            <Text size="text-xs" weight={600} uppercase>
              {content.title}
            </Text>
          )}

          <Text color="sand-12">{content.description}</Text>
        </Flex>

        <Dialog.Root>
          <Dialog.Trigger asChild>
            <Button
              iconLeft={<PencilSimple />}
              label={content.fillButtonLabel}
              variant="affirmative"
            />
          </Dialog.Trigger>

          <Dialog.Content size="s" title={content.title ?? ''}>
            {content.forms.map((form, index) => (
              <RequestDataForm form={form} key={index} />
            ))}
          </Dialog.Content>
        </Dialog.Root>
      </Flex>
    </Card>
  );
};

type RequestDataFormProps = {
  form: z.infer<typeof requestDataSchema>['request_data']['forms'][number];
};

function useRequestDataForm(props: RequestDataFormProps) {
  const hasWarned = useRef(false);
  const jsonUrl = 'json_url' in props.form ? props.form.json_url : null;
  const formQuery = trpc.protocol.loadJson.useQuery(
    {
      url: jsonUrl!,
    },
    {
      enabled: !!jsonUrl,
    },
  );

  const parsed = formQuery.data
    ? requestDataFormSchema.safeParse(formQuery.data)
    : null;

  const loadedFormWithOverrides = parsed?.data
    ? {
        ...parsed.data,
        ...props.form,
        fields: [...(parsed.data.fields ?? []), ...(props.form.fields ?? [])],
      }
    : null;

  const form = 'json_url' in props.form ? loadedFormWithOverrides : props.form;

  if (parsed?.error && !hasWarned.current) {
    console.error(
      `JSON message failed to match ${CURRENT_AGENT_PROTOCOL_SCHEMA} => "request_data"`,
      parsed.error,
      parsed.data,
    );
    openToast({
      type: 'error',
      title: 'Failed to load form',
      description: 'Please try again later',
    });
    hasWarned.current = true;
  }

  return {
    form,
    isError: !!parsed?.error,
  };
}

const RequestDataForm = (props: RequestDataFormProps) => {
  // TODO: Render form fields
  // TODO: Decide if the UX would be better if the form was simply rendered inline (not inside a modal requiring a click)

  const { form } = useRequestDataForm(props);

  if (!form) {
    return <PlaceholderStack />;
  }

  return (
    <Form autoComplete="on">
      <Flex direction="column" gap="l">
        {(form.title || form.description) && (
          <Flex direction="column" gap="s">
            {form.title && (
              <Text size="text-xs" weight={600} uppercase>
                {form.title}
              </Text>
            )}
            {form.description && (
              <Text color="sand-12">{form.description}</Text>
            )}
          </Flex>
        )}

        <Text>{JSON.stringify(form)}</Text>
      </Flex>
    </Form>
  );
};
