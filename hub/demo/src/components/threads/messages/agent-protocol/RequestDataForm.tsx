'use client';

import { Button, Flex, Form } from '@near-pagoda/ui';
import { FormProvider, type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { type RequestDataResult } from './RequestData';
import { RequestDataFormSection } from './RequestDataFormSection';
import { type requestDataSchema } from './schema';
import s from './styles.module.scss';

type Props = {
  contentId: string;
  content: z.infer<typeof requestDataSchema>['request_data'];
  onCancel: () => unknown;
  onValidSubmit: (data: RequestDataResult) => unknown;
};

export const RequestDataForm = ({
  content,
  contentId,
  onCancel,
  onValidSubmit,
}: Props) => {
  const form = useForm<RequestDataResult>();

  const onSubmit: SubmitHandler<RequestDataResult> = (data) => {
    onValidSubmit(data);
  };

  return (
    <Form autoComplete="on" onSubmit={form.handleSubmit(onSubmit)}>
      <FormProvider {...form}>
        <Flex direction="column" gap="l" className={s.formSections}>
          {content.forms.map((form, index) => (
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
