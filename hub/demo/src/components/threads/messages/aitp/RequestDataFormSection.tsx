'use client';

import {
  Combobox,
  Flex,
  Input,
  InputTextarea,
  openToast,
  PlaceholderStack,
  Text,
  useComboboxOptionMapper,
} from '@near-pagoda/ui';
import { useEffect, useRef } from 'react';
import { Controller, useFormContext } from 'react-hook-form';
import { type z } from 'zod';

import { trpc } from '~/trpc/TRPCProvider';
import { validateEmail } from '~/utils/inputs';
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
        <RequestDataFormInput
          field={field}
          contentId={contentId}
          index={index}
          key={index}
        />
      ))}
    </Flex>
  );
};

type RequestDataFormInputProps = {
  contentId: string;
  field: NonNullable<
    z.infer<typeof requestDataSchema>['request_data']['forms'][number]['fields']
  >[number];
  index: number;
};

export const RequestDataFormInput = ({
  contentId,
  field,
  index,
}: RequestDataFormInputProps) => {
  const hookForm = useFormContext<RequestDataResult>();
  const name = inputNameForField(contentId, field, index);
  const comboboxOptions = useComboboxOptionMapper(field.options, (item) => ({
    value: item,
  }));

  if (field.type === 'select' || field.type === 'combobox') {
    return (
      <Controller
        control={hookForm.control}
        name={name}
        rules={{
          required: field.required ? 'Please select a value' : undefined,
        }}
        render={(control) => (
          <Combobox
            label={field.required ? field.label : `${field.label} (Optional)`}
            options={comboboxOptions}
            error={control.fieldState.error?.message}
            autoComplete={field.autocomplete}
            assistive={field.description}
            allowCustomInput={field.type === 'combobox'}
            {...control.field}
          />
        )}
      />
    );
  }

  if (field.type === 'textarea') {
    return (
      <InputTextarea
        label={field.required ? field.label : `${field.label} (Optional)`}
        autoComplete={field.autocomplete}
        assistive={field.description}
        error={hookForm.formState.errors[name]?.message}
        {...hookForm.register(name, {
          required: field.required ? 'Please enter a value' : undefined,
        })}
      />
    );
  }

  return (
    <Input
      label={field.required ? field.label : `${field.label} (Optional)`}
      autoComplete={field.autocomplete}
      assistive={field.description}
      type={field.type}
      error={hookForm.formState.errors[name]?.message}
      {...hookForm.register(name, {
        required: field.required ? 'Please enter a value' : undefined,
        ...(field.type === 'email' ? { validate: validateEmail } : undefined),
      })}
    />
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
  return stringToHtmlAttribute(contentId + field.id + index);
}
