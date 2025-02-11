'use client';

import { Button, Flex, Form, PlaceholderStack } from '@near-pagoda/ui';
import { useEffect, useState } from 'react';
import { FormProvider, type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { ErrorMessage } from '~/components/ErrorMessage';
import { useThreadsStore } from '~/stores/threads';
import { trpc } from '~/trpc/TRPCProvider';

import {
  RequestDataFormSection,
  requestDataInputNameForField,
} from './RequestDataFormSection';
import { CURRENT_AGENT_PROTOCOL_SCHEMA } from './schema/base';
import {
  type dataSchema,
  requestDataFormSchema,
  type requestDataSchema,
} from './schema/data';
import s from './styles.module.scss';

type Props = {
  contentId: string;
  content: z.infer<typeof requestDataSchema>['request_data'];
  onCancel: () => unknown;
  onValidSubmit: () => unknown;
};

export type RequestDataFormSchema = Record<string, string>;

export const RequestDataForm = ({
  content,
  contentId,
  onCancel,
  onValidSubmit,
}: Props) => {
  const { forms, isLoading, isError } = useRequestDataForms(content);
  const hookForm = useForm<RequestDataFormSchema>();
  const addMessage = useThreadsStore((store) => store.addMessage);

  const onSubmit: SubmitHandler<RequestDataFormSchema> = async (data) => {
    if (!addMessage) return;

    const result: z.infer<typeof dataSchema> = {
      $schema: CURRENT_AGENT_PROTOCOL_SCHEMA,
      data: {
        request_data_id: content.id,
        fields: [],
      },
    };

    forms?.forEach((form) => {
      form.fields?.forEach((field, index) => {
        const name = requestDataInputNameForField(contentId, field, index);
        result.data.fields.push({
          id: field.id,
          label: field.label,
          value: data[name],
        });
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

  if (!forms?.length) return null;

  return (
    <Form autoComplete="on" onSubmit={hookForm.handleSubmit(onSubmit)}>
      <FormProvider {...hookForm}>
        <Flex direction="column" gap="l" className={s.formSections}>
          {forms.map((form, index) => (
            <RequestDataFormSection
              content={content}
              contentId={contentId}
              form={form}
              key={index}
            />
          ))}

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

function useRequestDataForms(content: Props['content']) {
  const jsonUrls = content.forms
    .map((f) => f.json_url)
    .filter((url) => typeof url === 'string');

  const formsQuery = trpc.aitp.loadJson.useQuery(
    {
      urls: jsonUrls,
    },
    {
      enabled: jsonUrls.length > 0,
    },
  );

  const [isError, setIsError] = useState(false);
  const isLoading = formsQuery.isLoading;

  useEffect(() => {
    if (formsQuery.error) {
      console.error(formsQuery.error);
      setIsError(true);
    }
  }, [formsQuery.error]);

  if (isLoading || isError) {
    return {
      isError,
      isLoading,
    };
  }

  const forms = content.forms
    .map((form) => {
      if (!form.json_url) return form;

      const fetched = formsQuery.data?.find(
        (data) => data.url === form.json_url,
      );

      const parsed = fetched
        ? requestDataFormSchema.safeParse(fetched.data)
        : null;

      if (parsed?.error) {
        console.error(
          `JSON message failed to match ${CURRENT_AGENT_PROTOCOL_SCHEMA} => "request_data"`,
          fetched,
          parsed.error,
        );
        setIsError(true);
      }

      const fetchedForm = parsed?.data
        ? {
            ...parsed.data,
            ...form,
            fields: [...(parsed.data.fields ?? []), ...(form.fields ?? [])],
          }
        : null;

      return fetchedForm;
    })
    .filter((form) => form !== null);

  return {
    forms,
  };
}
