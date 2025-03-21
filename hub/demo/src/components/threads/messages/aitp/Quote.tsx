'use client';

import {
  Badge,
  Button,
  Flex,
  handleClientError,
  ImageIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import { formatDollar } from '@nearai/ui/utils';
import {
  ArrowRight,
  ArrowsClockwise,
  CheckCircle,
  CurrencyDollar,
  PencilSimple,
  Wallet,
  Warning,
} from '@phosphor-icons/react';
import { useMutation } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { type z } from 'zod';

import { useQueryParams } from '@/hooks/url';
import {
  useThreadMessageContentFilter,
  useThreadsStore,
} from '@/stores/threads';
import { useWalletStore } from '@/stores/wallet';
import {
  dollarsToUsdcAtomicAmount,
  MAINNET_NEAR_USDC_CONTRACT_ID,
} from '@/utils/usdc';
import {
  generateWalletTransactionCallbackUrl,
  UNSET_WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS,
  WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS,
  type WalletTransactionRequestOrigin,
} from '@/utils/wallet';

import { Message } from './Message';
import {
  CURRENT_AITP_PAYMENTS_SCHEMA_URL,
  paymentAuthorizationSchema,
  type quoteSchema,
} from './schema/payments';

type Props = {
  content: z.infer<typeof quoteSchema>['quote'];
};

export const Quote = ({ content }: Props) => {
  const addMessage = useThreadsStore((store) => store.addMessage);
  const wallet = useWalletStore((store) => store.wallet);
  const walletModal = useWalletStore((store) => store.modal);
  const walletAccount = useWalletStore((store) => store.account);
  const loadUsdcBalance = useWalletStore((store) => store.loadUsdcBalance);
  const { queryParams, updateQueryPath } = useQueryParams([
    'threadId',
    ...WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS,
  ]);
  const lastSuccessfulTransactionIdRef = useRef('');
  const usdcBalanceDollars = useWalletStore(
    (store) => store.usdcBalanceDollars,
  );
  const [isRefreshingUsdcBalance, setIsRefreshingUsdcBalance] = useState(false);
  const amount = content.payment_plans?.[0]?.amount;

  const threadId = queryParams.threadId ?? '';
  const paymentConfirmation = useThreadMessageContentFilter(
    threadId,
    (json) => {
      if (json?.payment_confirmation) {
        const { data } = paymentAuthorizationSchema.safeParse(json);
        if (data?.payment_authorization.quote_id === content.quote_id) {
          return data;
        }
      }
    },
  )[0];

  const refreshUsdcBalanceVisually = async () => {
    setIsRefreshingUsdcBalance(true);
    await loadUsdcBalance();
    setIsRefreshingUsdcBalance(false);
  };

  const changeWallet = async () => {
    if (wallet) {
      await wallet.signOut();
    }
    walletModal?.show();
  };

  const onTransactionSuccess = useCallback(
    (transactionId: string) => {
      if (typeof amount !== 'number') return;
      if (!addMessage) return;
      if (!walletAccount?.accountId) return;
      if (lastSuccessfulTransactionIdRef.current === transactionId) return;
      lastSuccessfulTransactionIdRef.current = transactionId;

      const aitpResult: z.infer<typeof paymentAuthorizationSchema> = {
        $schema: CURRENT_AITP_PAYMENTS_SCHEMA_URL,
        payment_authorization: {
          quote_id: content.quote_id,
          result: 'success',
          timestamp: new Date().toISOString(),
          details: [
            {
              account_id: walletAccount.accountId,
              amount,
              network: 'NEAR',
              token_type: 'USDC',
              transaction_id: transactionId,
            },
          ],
        },
      };

      void addMessage({
        new_message: JSON.stringify(aitpResult),
      });
    },
    [addMessage, content.quote_id, walletAccount?.accountId, amount],
  );

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
        USDC native contract and swap NEAR for USDC. Example flow: https://app.ref.finance/#near
      */

      const result = await wallet!.signAndSendTransaction({
        signerId: walletAccount!.accountId,
        receiverId: MAINNET_NEAR_USDC_CONTRACT_ID,
        actions: [
          {
            type: 'FunctionCall',
            params: {
              methodName: 'ft_transfer',
              args: {
                receiver_id: content.payee_id,
                amount: dollarsToUsdcAtomicAmount(amount).toString(),
                memo: `Quote ID: ${content.quote_id}`,
              },
              gas: '300000000000000',
              deposit: '1',
            },
          },
        ],
        callbackUrl: generateWalletTransactionCallbackUrl(
          'quote',
          content.quote_id,
        ),
      });

      if (!result) {
        throw new Error('Undefined transaction result');
      }

      return result;
    },

    onSuccess: (result) => {
      onTransactionSuccess(result.transaction_outcome.id);
      void loadUsdcBalance();
    },

    onError: (error) => {
      if (error.message === 'User cancelled the action') return;
      void loadUsdcBalance();
      handleClientError({ error, title: 'Failed to send transaction' });
    },
  });

  useEffect(() => {
    // This logic handles full page redirect wallet flows like MyNearWallet

    const transactionId = queryParams.transactionHashes
      ?.split(',')
      .pop()
      ?.trim();

    if (
      transactionId &&
      queryParams.transactionRequestOrigin ===
        ('quote' satisfies WalletTransactionRequestOrigin) &&
      queryParams.transactionRequestId === content.quote_id
    ) {
      onTransactionSuccess(transactionId);
      updateQueryPath(
        { ...UNSET_WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS },
        'replace',
        false,
      );
    }
  }, [queryParams, content, onTransactionSuccess, updateQueryPath]);

  const successfulTransactionId =
    paymentConfirmation?.payment_authorization.details[0]?.transaction_id ||
    sendUsdcMutation.data?.transaction_outcome.id;

  const walletHasSufficientUsdcBalance =
    typeof amount === 'number' ? usdcBalanceDollars >= amount : false;

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
        <Text color="sand-12">{content.payee_id}</Text>
      </Flex>

      {successfulTransactionId ? (
        <Flex direction="column" gap="m" align="start">
          <Tooltip content="View transaction details">
            <Button
              label="Paid"
              iconLeft={<CheckCircle />}
              variant="affirmative"
              size="small"
              fill="outline"
              href={`https://nearblocks.io/txns/${successfulTransactionId}`}
              target="_blank"
            />
          </Tooltip>
        </Flex>
      ) : (
        <Flex direction="column" gap="m" align="start">
          {wallet && walletAccount ? (
            <>
              <Flex direction="column" gap="s">
                <Flex direction="column" gap="xs">
                  <Text size="text-xs">Payment Method</Text>

                  <Flex align="center" gap="s">
                    <ImageIcon
                      src={wallet.metadata.iconUrl}
                      alt={wallet.metadata.name}
                    />

                    <Flex direction="column">
                      <Text
                        size="text-s"
                        weight={600}
                        color="sand-12"
                        clampLines={1}
                      >
                        {walletAccount.accountId}
                      </Text>
                      <Text size="text-xs" clampLines={1}>
                        {wallet.metadata.name}
                      </Text>
                    </Flex>

                    <Tooltip asChild content="Change payment method">
                      <Button
                        label="Change"
                        icon={<PencilSimple weight="duotone" />}
                        variant="primary"
                        fill="outline"
                        size="small"
                        onClick={changeWallet}
                        disabled={sendUsdcMutation.isPending}
                      />
                    </Tooltip>

                    <Tooltip content="Add USDC funds via REF Finance">
                      <Button
                        size="small"
                        variant="affirmative"
                        fill="outline"
                        label="Add Funds"
                        icon={<CurrencyDollar weight="duotone" />}
                        href="https://app.ref.finance/#near"
                        target="_blank"
                      />
                    </Tooltip>
                  </Flex>
                </Flex>

                {!walletHasSufficientUsdcBalance && (
                  <Flex align="center" gap="xs">
                    <Badge
                      label={`Insufficient Funds: ${formatDollar(usdcBalanceDollars)} USDC`}
                      variant="warning"
                      iconLeft={<Warning />}
                      style={{ alignSelf: 'start' }}
                    />

                    <Tooltip asChild content="Reload current balance">
                      <Button
                        label="Refresh Balance"
                        icon={<ArrowsClockwise />}
                        variant="primary"
                        fill="ghost"
                        size="x-small"
                        onClick={refreshUsdcBalanceVisually}
                        loading={isRefreshingUsdcBalance}
                      />
                    </Tooltip>
                  </Flex>
                )}
              </Flex>

              <Button
                label="Pay Now"
                variant="affirmative"
                iconRight={<ArrowRight />}
                onClick={() => sendUsdcMutation.mutate()}
                loading={sendUsdcMutation.isPending}
                disabled={!walletHasSufficientUsdcBalance}
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
