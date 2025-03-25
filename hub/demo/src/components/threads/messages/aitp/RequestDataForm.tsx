'use client';

import { Button, Flex, Form, PlaceholderStack } from '@nearai/ui';
import { useEffect, useState } from 'react';
import { FormProvider, type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { ErrorMessage } from '@/components/ErrorMessage';
import { useThreadsStore } from '@/stores/threads';
import { trpc } from '@/trpc/TRPCProvider';

import { useThreadMessageContent } from '../../ThreadMessageContentProvider';
import {
  RequestDataFormSection,
  requestDataInputNameForField,
} from './RequestDataFormSection';
import {
  CURRENT_AITP_DATA_SCHEMA_URL,
  type dataSchema,
  requestDataFormSchema,
  type requestDataSchema,
} from './schema/data';
import s from './styles.module.scss';

type Props = {
  content: z.infer<typeof requestDataSchema>['request_data'];
  defaultFieldValues?: z.infer<typeof dataSchema>['data']['fields'];
  onCancel: () => unknown;
  onValidSubmit: () => unknown;
};

export type RequestDataHookFormSchema = Record<string, string>;

export const RequestDataForm = ({
  content,
  defaultFieldValues,
  onCancel,
  onValidSubmit,
}: Props) => {
  const { messageContentId } = useThreadMessageContent();
  const { form, isLoading, isError } = useRequestDataForm(content);
  const hookForm = useForm<RequestDataHookFormSchema>();
  const addMessage = useThreadsStore((store) => store.addMessage);

  const onSubmit: SubmitHandler<RequestDataHookFormSchema> = async (data) => {
    if (!addMessage) return;

    const result: z.infer<typeof dataSchema> = {
      $schema: CURRENT_AITP_DATA_SCHEMA_URL,
      data: {
        request_data_id: content.id,
        fields: [],
      },
    };

    form?.fields?.forEach((field, index) => {
      const name = requestDataInputNameForField(messageContentId, field, index);
      result.data.fields.push({
        id: field.id,
        label: field.label,
        value: data[name],
      });
    });

    void addMessage({
      new_message: JSON.stringify(result),
    });

    onValidSubmit();
  };

  if (isLoading) {
    return <PlaceholderStack />;
  }

  if (isError) {
    return (
      <ErrorMessage error="Failed to load form. Please try again later." />
    );
  }

  if (!form) return null;

  return (
    <Form autoComplete="on" onSubmit={hookForm.handleSubmit(onSubmit)}>
      <FormProvider {...hookForm}>
        <Flex direction="column" gap="l" className={s.formSections}>
          <RequestDataFormSection
            content={content}
            form={form}
            defaultFieldValues={defaultFieldValues}
          />

          <Flex justify="space-between">
            <Button
              label="Cancel"
              onClick={onCancel}
              variant="secondary"
              fill="outline"
            />

            <Button label="Submit" type="submit" variant="affirmative" />
          </Flex>
        </Flex>
      </FormProvider>
    </Form>
  );
};

function useRequestDataForm(content: Props['content']) {
  const formQuery = trpc.aitp.loadJson.useQuery(
    {
      url: content.form.json_url!,
    },
    {
      enabled: !!content.form.json_url,
    },
  );

  const [isError, setIsError] = useState(false);
  const isLoading = formQuery.isLoading;

  useEffect(() => {
    if (formQuery.error) {
      console.error(formQuery.error);
      setIsError(true);
    }
  }, [formQuery.error]);

  if (isLoading || isError) {
    return {
      isError,
      isLoading,
    };
  }

  if (!content.form.json_url) {
    return {
      form: content.form,
    };
  }

  const parsed = formQuery.data
    ? requestDataFormSchema.safeParse(formQuery.data)
    : null;

  if (parsed?.error) {
    console.error(
      `The JSON provided by form.json_url (${content.form.json_url}) failed to match the AITP schema`,
      formQuery.data,
      parsed.error,
    );
    setIsError(true);
  }

  const fetchedForm = parsed?.data
    ? {
        ...parsed.data,
        ...content.form,
        fields: [...(parsed.data.fields ?? []), ...(content.form.fields ?? [])],
      }
    : null;

  return {
    form: fetchedForm,
  };
}
