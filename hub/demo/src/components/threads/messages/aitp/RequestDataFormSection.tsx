'use client';

import {
  Combobox,
  Flex,
  Input,
  InputTextarea,
  useComboboxOptionMapper,
} from '@nearai/ui';
import { useEffect } from 'react';
import { Controller, useFormContext } from 'react-hook-form';
import { type z } from 'zod';

import { validateEmail } from '@/utils/inputs';
import { stringToHtmlAttribute } from '@/utils/string';

import { useThreadMessageContent } from '../../ThreadMessageContentProvider';
import { type RequestDataHookFormSchema } from './RequestDataForm';
import {
  type dataSchema,
  type requestDataFormFieldSchema,
  type requestDataFormSchema,
  type requestDataSchema,
} from './schema/data';

type Props = {
  content: z.infer<typeof requestDataSchema>['request_data'];
  defaultFieldValues?: z.infer<typeof dataSchema>['data']['fields'];
  form: z.infer<typeof requestDataFormSchema>;
};

export const RequestDataFormSection = ({ defaultFieldValues, form }: Props) => {
  const { messageContentId } = useThreadMessageContent();
  const hookForm = useFormContext<RequestDataHookFormSchema>();

  useEffect(() => {
    if (hookForm.formState.isDirty) return;

    form.fields?.forEach((field, index) => {
      const defaultValue =
        defaultFieldValues?.find((f) => f.id === field.id)?.value ||
        field.default_value;

      if (defaultValue) {
        hookForm.setValue(
          requestDataInputNameForField(messageContentId, field, index),
          defaultValue,
          {
            shouldDirty: true,
          },
        );
      }
    });
  }, [defaultFieldValues, messageContentId, hookForm, form]);

  return (
    <Flex direction="column" gap="m">
      {form.fields?.map((field, index) => (
        <RequestDataFormInput field={field} index={index} key={index} />
      ))}
    </Flex>
  );
};

type RequestDataFormInputProps = {
  field: z.infer<typeof requestDataFormFieldSchema>;
  index: number;
};

export const RequestDataFormInput = ({
  field,
  index,
}: RequestDataFormInputProps) => {
  const { messageContentId } = useThreadMessageContent();
  const hookForm = useFormContext<RequestDataHookFormSchema>();
  const name = requestDataInputNameForField(messageContentId, field, index);

  const comboboxOptions = useComboboxOptionMapper(field.options, (item) => {
    if (typeof item === 'string') {
      return {
        label: item,
        value: item,
      };
    }
    return {
      label: item.label,
      value: item.value,
    };
  });
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
  messageContentId: string,
  field: z.infer<typeof requestDataFormFieldSchema>,
  index: number,
) {
  return stringToHtmlAttribute(`${messageContentId}_${field.id}_${index}`);
}
