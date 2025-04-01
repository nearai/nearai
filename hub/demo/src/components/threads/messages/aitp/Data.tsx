'use client';

import { Button, Dialog, Flex, SvgIcon, Text } from '@nearai/ui';
import { PencilSimple } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { useQueryParams } from '@/hooks/url';
import { useThreadMessageContentFilter } from '@/stores/threads';

import { Message } from './Message';
import { RequestDataForm } from './RequestDataForm';
import { type dataSchema, requestDataSchema } from './schema/data';

type Props = {
  content: z.infer<typeof dataSchema>['data'];
};

export const Data = ({ content }: Props) => {
  const [formIsOpen, setFormIsOpen] = useState(false);
  const { queryParams } = useQueryParams(['threadId']);
  const threadId = queryParams.threadId ?? '';

  const requestData = useThreadMessageContentFilter(threadId, (json) => {
    if (json?.request_data) {
      const { data } = requestDataSchema.safeParse(json);
      if (data?.request_data.id === content.request_data_id) {
        return data;
      }
    }
  })[0];

  const fieldsWithValues = content.fields.filter((field) => field.value);
  const fields =
    fieldsWithValues.length > 0 ? fieldsWithValues : content.fields;

  return (
    <Message>
      <Flex direction="column" gap="m" align="start">
        <Flex align="center" gap="s">
          <SvgIcon
            icon={<PencilSimple weight="duotone" />}
            size="xs"
            color="sand-11"
          />
          <Text size="text-xs" weight={600} uppercase>
            {requestData?.request_data.title || 'Data'}
          </Text>
        </Flex>

        {fields.map((field, index) => (
          <Flex direction="column" key={index}>
            <Text size="text-xs">{field.label || field.id}</Text>

            {field.value ? (
              <Text color="sand-12">{field.value}</Text>
            ) : (
              <Text color="sand-10">--</Text>
            )}
          </Flex>
        ))}

        {requestData && (
          <>
            <Button
              label="Edit"
              size="small"
              fill="outline"
              onClick={() => setFormIsOpen(true)}
            />

            <Dialog.Root open={formIsOpen} onOpenChange={setFormIsOpen}>
              <Dialog.Content
                size="s"
                title={requestData.request_data.title ?? ''}
              >
                <RequestDataForm
                  content={requestData.request_data}
                  defaultFieldValues={content.fields}
                  onCancel={() => setFormIsOpen(false)}
                  onValidSubmit={() => setFormIsOpen(false)}
                />
              </Dialog.Content>
            </Dialog.Root>
          </>
        )}
      </Flex>
    </Message>
  );
};
