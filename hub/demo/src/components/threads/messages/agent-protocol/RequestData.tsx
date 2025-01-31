'use client';

import { Button, Card, Dialog, Flex, Text } from '@near-pagoda/ui';
import { PencilSimple } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { RequestDataForm } from './RequestDataForm';
import { type requestDataSchema } from './schema';

export type RequestDataResult = Record<string, string>;

type Props = {
  contentId: string;
  content: z.infer<typeof requestDataSchema>['request_data'];
};

export const RequestData = ({ content, contentId }: Props) => {
  const [formIsOpen, setFormIsOpen] = useState(false);

  const onValidSubmit = (data: RequestDataResult) => {
    console.log(data);
    setFormIsOpen(false);
  };

  return (
    <Card animateIn>
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
              contentId={contentId}
              onValidSubmit={onValidSubmit}
            />
          </Dialog.Content>
        </Dialog.Root>
      </Flex>
    </Card>
  );
};
