'use client';

import { Flex, SvgIcon, Text } from '@near-pagoda/ui';
import { PencilSimple } from '@phosphor-icons/react';
import { type z } from 'zod';

import { Message } from './Message';
import { type dataSchema } from './schema/data';

type Props = {
  content: z.infer<typeof dataSchema>['data'];
};

export const Data = ({ content }: Props) => {
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
            Data
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
      </Flex>
    </Message>
  );
};
