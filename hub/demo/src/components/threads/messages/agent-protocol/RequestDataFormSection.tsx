'use client';

import {
  Combobox,
  Flex,
  Input,
  InputTextarea,
  openToast,
  PlaceholderStack,
  Text,
} from '@near-pagoda/ui';
import { Fragment, useEffect, useRef } from 'react';
import { Controller, useFormContext } from 'react-hook-form';
import { type z } from 'zod';

import { trpc } from '~/trpc/TRPCProvider';
import { stringToHtmlAttribute } from '~/utils/string';

import { type RequestDataResult } from './RequestData';
import {
  CURRENT_AGENT_PROTOCOL_SCHEMA,
  type requestDataFormFieldSchema,
  requestDataFormSchema,
  type requestDataSchema,
} from './schema';

type Props = {
  contentId: string;
  content: z.infer<typeof requestDataSchema>['request_data'];
  form: z.infer<typeof requestDataSchema>['request_data']['forms'][number];
};

export const RequestDataFormSection = ({ contentId, ...props }: Props) => {
  // TODO: Add submit/cancel button
  // TODO: Form validation (required, email, etc)
  // TODO: Form default values (useEffect())
  // TODO: Fix autocomplete form styles
  // TODO: Fix 1Password button click closing modal bug (the click registers as outside of the modal since the button is fixed outside of the dialog dom node)
  // TODO: Decide if the UX would be better if the form was simply rendered inline (not inside a modal requiring a click)

  const hookForm = useFormContext<RequestDataResult>();
  const { form } = useRequestDataForm(props);

  useEffect(() => {
    if (!form) return;
    if (!hookForm.formState.isDirty) return;

    form.fields?.forEach((field, index) => {
      if (field.default_value) {
        hookForm.setValue(
          inputNameForField(contentId, field, index),
          field.default_value,
          {
            shouldDirty: true,
          },
        );
      }
    });
  }, [contentId, hookForm, form]);

  if (!form) {
    return <PlaceholderStack />;
  }

  return (
    <Flex direction="column" gap="m">
      {(form.title || form.description) && (
        <Flex direction="column" gap="s">
          {form.title && (
            <Text size="text-xs" weight={600} uppercase>
              {form.title}
            </Text>
          )}
          {form.description && <Text color="sand-12">{form.description}</Text>}
        </Flex>
      )}

      {form.fields?.map((field, index) => (
        <Fragment key={index}>
          {field.type === 'select' && (
            <Controller
              control={hookForm.control}
              name={inputNameForField(contentId, field, index)}
              rules={{
                required: field.required ? 'Please select a value' : undefined,
              }}
              render={(control) => (
                <Combobox
                  label={
                    field.required ? field.label : `${field.label} (Optional)`
                  }
                  items={
                    field.options?.map((option) => ({ value: option })) ?? []
                  }
                  autoComplete={field.autocomplete}
                  assistive={field.description}
                  {...control.field}
                />
              )}
            />
          )}

          {field.type === 'textarea' && (
            <InputTextarea
              label={field.required ? field.label : `${field.label} (Optional)`}
              autoComplete={field.autocomplete}
              assistive={field.description}
              {...hookForm.register(
                inputNameForField(contentId, field, index),
                {
                  required: field.required ? 'Please enter a value' : undefined,
                },
              )}
            />
          )}

          {field.type !== 'select' && field.type !== 'textarea' && (
            <Input
              label={field.required ? field.label : `${field.label} (Optional)`}
              autoComplete={field.autocomplete}
              assistive={field.description}
              type={field.type}
              {...hookForm.register(
                inputNameForField(contentId, field, index),
                {
                  required: field.required ? 'Please enter a value' : undefined,
                },
              )}
            />
          )}
        </Fragment>
      ))}
    </Flex>
  );
};

function useRequestDataForm(props: Pick<Props, 'form'>) {
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

function inputNameForField(
  contentId: string,
  field: z.infer<typeof requestDataFormFieldSchema>,
  index: number,
) {
  return stringToHtmlAttribute(contentId + field.label + index);
}
