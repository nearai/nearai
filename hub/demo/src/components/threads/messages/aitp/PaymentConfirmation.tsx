'use client';

import {
  Badge,
  Flex,
  SvgIcon,
  Text,
  Timestamp,
  Tooltip,
} from '@near-pagoda/ui';
import { Wallet } from '@phosphor-icons/react';
import { type z } from 'zod';

import { Message } from './Message';
import { type paymentConfirmationSchema } from './schema/payment';

type Props = {
  content: z.infer<typeof paymentConfirmationSchema>['payment_confirmation'];
};

export const PaymentConfirmation = ({ content }: Props) => {
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
            Payment Confirmation
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
            {content.message}
          </Flex>
        )}

        <Flex direction="column">
          <Text size="text-xs">Transaction ID</Text>
          <Tooltip content="View transaction details">
            <Text
              href={`https://nearblocks.io/txns/${content.transaction_id}`}
              target="_blank"
            >
              {content.transaction_id}
            </Text>
          </Tooltip>
        </Flex>

        <Flex direction="column">
          <Text size="text-xs">Sent On</Text>
          <Timestamp date={new Date(content.timestamp)} />
        </Flex>
      </Flex>
    </Message>
  );
};
