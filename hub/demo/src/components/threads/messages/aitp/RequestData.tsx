'use client';

import { Button, Dialog, Flex, Text } from '@nearai/ui';
import { PencilSimple } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { Message } from './Message';
import { RequestDataForm } from './RequestDataForm';
import { type requestDataSchema } from './schema/data';

type Props = {
  content: z.infer<typeof requestDataSchema>['request_data'];
};

export const RequestData = ({ content }: Props) => {
  const [formIsOpen, setFormIsOpen] = useState(false);

  return (
    <Message>
      <Flex direction="column" gap="m" align="start">
        <Flex direction="column" gap="s">
          {content.title && (
            <Text size="text-xs" weight={600} uppercase>
              {content.title}
            </Text>
          )}

          <Text color="sand-12">{content.description}</Text>
        </Flex>

        <Button
          iconLeft={<PencilSimple />}
          label={content.fillButtonLabel}
          variant="affirmative"
          onClick={() => setFormIsOpen(true)}
        />

        <Dialog.Root open={formIsOpen} onOpenChange={setFormIsOpen}>
          <Dialog.Content size="s" title={content.title ?? ''}>
            <RequestDataForm
              content={content}
              onCancel={() => setFormIsOpen(false)}
              onValidSubmit={() => setFormIsOpen(false)}
            />
          </Dialog.Content>
        </Dialog.Root>
      </Flex>
    </Message>
  );
};
