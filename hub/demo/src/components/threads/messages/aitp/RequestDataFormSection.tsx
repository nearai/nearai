'use client';

import {
  Combobox,
  Flex,
  Input,
  InputTextarea,
  Text,
  useComboboxOptionMapper,
} from '@near-pagoda/ui';
import { useEffect } from 'react';
import { Controller, useFormContext } from 'react-hook-form';
import { type z } from 'zod';

import { validateEmail } from '~/utils/inputs';
import { stringToHtmlAttribute } from '~/utils/string';

import { type RequestDataFormSchema } from './RequestDataForm';
import {
  type requestDataFormFieldSchema,
  type requestDataFormSchema,
  type requestDataSchema,
} from './schema/data';

type Props = {
  contentId: string;
  content: z.infer<typeof requestDataSchema>['request_data'];
  form: z.infer<typeof requestDataFormSchema>;
};

export const RequestDataFormSection = ({ contentId, form }: Props) => {
  const hookForm = useFormContext<RequestDataFormSchema>();

  useEffect(() => {
    if (!hookForm.formState.isDirty) return;

    form.fields?.forEach((field, index) => {
      if (field.default_value) {
        hookForm.setValue(
          requestDataInputNameForField(contentId, field, index),
          field.default_value,
          {
            shouldDirty: true,
          },
        );
      }
    });
  }, [contentId, hookForm, form]);

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
  const hookForm = useFormContext<RequestDataFormSchema>();
  const name = requestDataInputNameForField(contentId, field, index);
  const comboboxOptions = useComboboxOptionMapper(field.options, (item) => ({
    value: item,
  }));
  const label = field.label || field.id;

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
            label={field.required ? label : `${label} (Optional)`}
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
        label={field.required ? label : `${label} (Optional)`}
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
      label={field.required ? label : `${label} (Optional)`}
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

export function requestDataInputNameForField(
  contentId: string,
  field: z.infer<typeof requestDataFormFieldSchema>,
  index: number,
) {
  return stringToHtmlAttribute(contentId + field.id + index);
}
