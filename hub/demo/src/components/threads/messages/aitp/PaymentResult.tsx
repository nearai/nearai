'use client';

import { Badge, Flex, SvgIcon, Text, Timestamp } from '@nearai/ui';
import { Wallet } from '@phosphor-icons/react';
import { type z } from 'zod';

import { Message } from './Message';
import { type paymentResultSchema } from './schema/payments';

type Props = {
  content: z.infer<typeof paymentResultSchema>['payment_result'];
};

export const PaymentResult = ({ content }: Props) => {
  return (
    <Message>
      <Flex direction="column" gap="m" align="start">
        <Flex align="center" gap="s">
          <SvgIcon
            icon={<Wallet weight="duotone" />}
            size="xs"
            color="sand-11"
          />
          <Text size="text-xs" weight={600} uppercase>
            Payment Result
          </Text>
        </Flex>

        {content.result === 'success' ? (
          <Badge label="Success" variant="success" />
        ) : (
          <Badge label="Failure" variant="alert" />
        )}

        {content.message && (
          <Flex direction="column">
            <Text size="text-xs">Message</Text>
            <Text color="sand-12">{content.message}</Text>
          </Flex>
        )}

        {content.details.map((detail, index) => (
          <Flex direction="column" key={index}>
            <Text size="text-xs">{detail.label}</Text>
            <Text
              color="sand-12"
              href={detail.url}
              target={detail.url ? '_blank' : undefined}
            >
              {detail.value}
            </Text>
          </Flex>
        ))}

        <Flex direction="column">
          <Text size="text-xs">Processed On</Text>
          <Text color="sand-12">
            <Timestamp date={new Date(content.timestamp)} />
          </Text>
        </Flex>
      </Flex>
    </Message>
  );
};
