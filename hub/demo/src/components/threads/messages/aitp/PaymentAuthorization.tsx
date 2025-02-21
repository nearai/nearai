'use client';

import {
  Badge,
  Flex,
  SvgIcon,
  Text,
  Timestamp,
  Tooltip,
} from '@near-pagoda/ui';
import { formatDollar } from '@near-pagoda/ui/utils';
import { Wallet } from '@phosphor-icons/react';
import { Fragment } from 'react';
import { type z } from 'zod';

import { Message } from './Message';
import { type paymentAuthorizationSchema } from './schema/payment';

type Props = {
  content: z.infer<typeof paymentAuthorizationSchema>['payment_authorization'];
};

export const PaymentAuthorization = ({ content }: Props) => {
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
            Payment Authorization
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
          <Fragment key={index}>
            <Flex direction="column">
              <Text size="text-xs">Payment Method</Text>
              <Text color="sand-12">
                {detail.network}, {detail.token_type}, {detail.account_id}
              </Text>
              <Tooltip content="View transaction details">
                <Text
                  href={`https://nearblocks.io/txns/${detail.transaction_id}`}
                  target="_blank"
                  family="monospace"
                >
                  {detail.transaction_id}
                </Text>
              </Tooltip>
            </Flex>

            <Flex direction="column">
              <Text size="text-xs">Amount</Text>
              <Text color="sand-12">{formatDollar(detail.amount)}</Text>
            </Flex>
          </Fragment>
        ))}

        <Flex direction="column">
          <Text size="text-xs">Authorized On</Text>
          <Text color="sand-12">
            <Timestamp date={new Date(content.timestamp)} />
          </Text>
        </Flex>
      </Flex>
    </Message>
  );
};
