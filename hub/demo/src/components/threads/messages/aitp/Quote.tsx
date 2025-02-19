'use client';

import {
  Button,
  Flex,
  handleClientError,
  SvgIcon,
  Text,
} from '@near-pagoda/ui';
import { formatDollar } from '@near-pagoda/ui/utils';
import { ArrowRight, Wallet } from '@phosphor-icons/react';
import { useMutation } from '@tanstack/react-query';
import { type z } from 'zod';

import { useThreadsStore } from '~/stores/threads';
import { useWalletStore } from '~/stores/wallet';

import { Message } from './Message';
import {
  CURRENT_AITP_PAYMENT_SCHEMA_URL,
  type paymentConfirmationSchema,
  type quoteSchema,
} from './schema/payment';

type Props = {
  content: z.infer<typeof quoteSchema>['quote'];
};

const NEAR_USDC_CONTRACT_ID =
  '17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1';

export const Quote = ({ content }: Props) => {
  const addMessage = useThreadsStore((store) => store.addMessage);
  const wallet = useWalletStore((store) => store.wallet);
  const walletModal = useWalletStore((store) => store.modal);
  const walletAccount = useWalletStore((store) => store.account);
  const amount = content.payment_plans?.[0]?.amount;

  const changeWallet = async () => {
    if (wallet) {
      await wallet.signOut();
    }
    walletModal?.show();
  };

  const sendUsdcMutation = useMutation({
    mutationFn: async () => {
      if (typeof amount !== 'number') {
        throw new Error(`Invalid amount passed to sendUsdcMutation: ${amount}`);
      }

      /*
        NOTE: As of now, the following signAndSendTransaction() will fail if 
        either the signerId (sender) or payee_id (receiver) are not registered 
        with the USDC contract.  

        TODO: Look into using signAndSendTransactions() to register user with 
        USDC native contract. Example flow: https://app.ref.finance/#near
      */

      const result = await wallet!.signAndSendTransaction({
        signerId: walletAccount!.accountId,
        receiverId: NEAR_USDC_CONTRACT_ID,
        actions: [
          {
            type: 'FunctionCall',
            params: {
              methodName: 'ft_transfer',
              args: {
                receiver_id: content.payee_id,
                amount: (amount * 1000000).toString(),
                memo: `Quote ID: ${content.quote_id}`,
              },
              gas: '300000000000000',
              deposit: '1',
            },
          },
        ],
      });

      if (!result) {
        throw new Error('Undefined transaction result');
      }

      return result;
    },

    onSuccess: (result) => {
      const aitpResult: z.infer<typeof paymentConfirmationSchema> = {
        $schema: CURRENT_AITP_PAYMENT_SCHEMA_URL,
        payment_confirmation: {
          quote_id: content.quote_id,
          result: 'success',
          transaction_id: result.transaction_outcome.id,
          timestamp: new Date().toISOString(),
        },
      };

      void addMessage!({
        new_message: JSON.stringify(aitpResult),
      });
    },

    onError: (error) => {
      if (error.message === 'User cancelled the action') return;
      handleClientError({ error, title: 'Failed to send transaction' });
    },
  });

  return (
    <Message>
      <Text size="text-xs" weight={600} uppercase>
        Payment Request
      </Text>

      <Flex direction="column">
        <Text size="text-xs">Amount</Text>
        <Text color="sand-12">{formatDollar(amount)}</Text>
      </Flex>

      <Flex direction="column">
        <Text size="text-xs">Payee</Text>

        <Flex align="center" gap="s">
          <SvgIcon
            icon={<ArrowRight weight="bold" />}
            size="xs"
            color="sand-10"
          />
          <Text color="sand-12">{content.payee_id}</Text>
        </Flex>
      </Flex>

      {!sendUsdcMutation.isSuccess && (
        <Flex direction="column" gap="m" align="start">
          {wallet && walletAccount ? (
            <>
              <Flex direction="column">
                <Text size="text-xs">Your Wallet</Text>

                <Flex align="center" gap="s">
                  <SvgIcon
                    icon={<Wallet weight="bold" />}
                    size="xs"
                    color="sand-10"
                  />

                  <Text color="sand-12">{walletAccount.accountId}</Text>

                  <Button
                    label="Change"
                    variant="primary"
                    size="x-small"
                    fill="outline"
                    onClick={changeWallet}
                    disabled={sendUsdcMutation.isPending}
                  />
                </Flex>
              </Flex>

              <Button
                label="Pay Now"
                variant="affirmative"
                iconRight={<ArrowRight />}
                onClick={() => sendUsdcMutation.mutate()}
                loading={sendUsdcMutation.isPending}
              />
            </>
          ) : (
            <Button
              iconLeft={<Wallet />}
              label="Connect Wallet"
              variant="primary"
              onClick={() => walletModal?.show()}
            />
          )}
        </Flex>
      )}
    </Message>
  );
};
