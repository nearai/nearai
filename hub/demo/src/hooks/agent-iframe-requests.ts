import { handleClientError } from '@near-pagoda/ui';
import { type FinalExecutionOutcome } from '@near-wallet-selector/core';
import { type UseMutationResult } from '@tanstack/react-query';
import { formatNearAmount } from 'near-api-js/lib/utils/format';
import { useCallback, useEffect, useState } from 'react';
import { type z } from 'zod';

import {
  type AgentRequestWithPermissions,
  checkAgentPermissions,
} from '~/components/AgentPermissionsModal';
import { type AgentChatMutationInput } from '~/components/AgentRunner';
import { type IframePostMessageEventHandler } from '~/components/lib/IframeWithBlob';
import { parseEntryId } from '~/lib/entries';
import {
  agentAddSecretsRequestModel,
  agentNearAccountRequestModel,
  agentNearSendTransactionsRequestModel,
  agentNearViewRequestModel,
  chatWithAgentModel,
  type entryModel,
} from '~/lib/models';
import { useNearStore } from '~/stores/near';
import { useWalletStore } from '~/stores/wallet';
import { api } from '~/trpc/react';
import { unreachable } from '~/utils/unreachable';

import { useQueryParams } from './url';

const PENDING_TRANSACTION_KEY = 'agent-transaction-request-pending-connection';

export type AgentActionType =
  | 'add_secrets'
  | 'near_account'
  | 'near_send_transactions'
  | 'near_view'
  | 'remote_agent_run'
  | 'refresh_thread_id';

export function useAgentRequestsWithIframe(
  currentEntry: z.infer<typeof entryModel> | undefined,
  chatMutation: UseMutationResult<
    unknown,
    Error,
    AgentChatMutationInput,
    unknown
  >,
  threadId: string | null | undefined,
) {
  const addSecretMutation = api.hub.addSecret.useMutation();
  const { queryParams, updateQueryPath } = useQueryParams([
    'account_id',
    'threadId',
    'public_key',
    'transactionHashes',
    'transactionRequestId',
  ]);
  const selector = useWalletStore((store) => store.selector);
  const wallet = useWalletStore((store) => store.wallet);
  const walletSignInModal = useWalletStore((store) => store.modal);
  const nearViewAccount = useNearStore((store) => store.viewAccount);
  const near = useNearStore((store) => store.near);
  const [iframePostMessage, setIframePostMessage] = useState<unknown>(null);
  const [iframeNonce, setIframeNonce] = useState<number | null>(null);
  const [agentRequestsNeedingPermissions, setAgentRequestsNeedingPermissions] =
    useState<AgentRequestWithPermissions[] | null>(null);
  const utils = api.useUtils();

  const handleWalletTransactionResponse = useCallback(
    (options: {
      result: FinalExecutionOutcome[] | string;
      requestId?: string | null;
    }) => {
      const transactionHashes =
        typeof options.result === 'string'
          ? options.result.split(',')
          : options.result.map((outcome) => outcome.transaction_outcome.id);

      setIframePostMessage({
        action: 'near_send_transactions_response',
        requestId: options.requestId,
        result: {
          transactionHashes,
        },
      });

      updateQueryPath(
        {
          account_id: undefined,
          public_key: undefined,
          transactionHashes: undefined,
          transactionRequestId: undefined,
        },
        'replace',
        false,
      );
    },
    [updateQueryPath],
  );

  const conditionallyProcessAgentRequests = async (
    requests: AgentRequestWithPermissions[],
    allowedBypass?: boolean,
  ) => {
    if (!currentEntry) return;

    const permissionsCheck = checkAgentPermissions(currentEntry, requests);

    if (allowedBypass ?? permissionsCheck.allowed) {
      requests.forEach(async ({ action, input }) => {
        if (action === 'add_secrets') {
          const addedKeys: string[] = [];
          const failedKeys: string[] = [];

          for (const secret of input.secrets) {
            try {
              const { name, namespace, version } = parseEntryId(secret.agentId);
              await addSecretMutation.mutateAsync({
                category: 'agent',
                key: secret.key,
                name,
                namespace,
                value: secret.value,
                version,
              });
              addedKeys.push(secret.key);
            } catch (error) {
              handleClientError({
                error,
                title: `Failed to save secret: ${secret.key}`,
              });
              failedKeys.push(secret.key);
            }
          }

          setIframePostMessage({
            action: 'add_secrets_response',
            requestId: input.requestId,
            result: {
              addedKeys,
              failedKeys,
            },
          });

          await utils.hub.secrets.refetch();

          if (input.reloadAgentOnSuccess) {
            setIframeNonce(Date.now()); // This will trigger the iframe to reload
          }
        } else if (action === 'remote_agent_run') {
          await chatMutation.mutateAsync(input);
        } else if (action === 'near_send_transactions') {
          if (wallet) {
            try {
              const callbackUrl = new URL(window.location.href);
              if (input.requestId) {
                callbackUrl.searchParams.set(
                  'transactionRequestId',
                  input.requestId,
                );
              }

              const result = await wallet.signAndSendTransactions({
                transactions: input.transactions,
                callbackUrl: callbackUrl.toString(),
              });

              if (result) {
                handleWalletTransactionResponse({
                  result,
                  requestId: input.requestId,
                });
              }
            } catch (error) {
              console.error(error);
            }
          } else {
            localStorage.setItem(
              PENDING_TRANSACTION_KEY,
              JSON.stringify(input),
            );
            walletSignInModal!.show();
          }
        } else {
          unreachable(action);
        }
      });
    } else {
      setAgentRequestsNeedingPermissions(requests);
    }
  };

  const onIframePostMessage: IframePostMessageEventHandler<{
    action: AgentActionType;
    data: unknown;
  }> = async (event) => {
    try {
      const action = event.data.action;

      if (action === 'near_send_transactions') {
        const input = agentNearSendTransactionsRequestModel.parse(
          event.data.data,
        );
        void conditionallyProcessAgentRequests([
          {
            action,
            input,
          },
        ]);
      } else if (action === 'near_view') {
        const input = agentNearViewRequestModel.parse(event.data.data);
        const result: unknown = await nearViewAccount!.viewFunction(input);
        setIframePostMessage({
          action: 'near_view_response',
          requestId: input.requestId,
          result,
        });
      } else if (action === 'near_account') {
        const input = agentNearAccountRequestModel.parse(event.data.data);
        let accountId = input.accountId;

        if (!accountId && selector) {
          const isSignedIn = selector.isSignedIn();
          if (isSignedIn) {
            const accounts = selector.store.getState().accounts;
            if (accounts.length > 0) {
              accountId = accounts[0]?.accountId ?? '';
            }
          }
        }

        if (near && accountId) {
          const account = await near.account(accountId);
          const accountBalance = await account.getAccountBalance();
          const yNEAR = accountBalance.total;
          const NEAR = formatNearAmount(yNEAR, 2).replace(/,/g, '');
          setIframePostMessage({
            action: 'near_account_response',
            requestId: input.requestId,
            result: { accountId, balance: NEAR, yNEAR },
          });
        } else {
          console.error('Missing data read `near_account`');
        }
      } else if (action === 'refresh_thread_id') {
        const input = chatWithAgentModel.partial().parse(event.data.data);
        if (input.thread_id) {
          void utils.hub.thread.invalidate();
          updateQueryPath({ threadId: input.thread_id }, 'replace', false);
        }
      } else if (action === 'remote_agent_run') {
        const input = chatWithAgentModel.parse(event.data.data);
        input.max_iterations = Number(input.max_iterations) || 1;
        input.thread_id = input.thread_id ?? threadId;
        void conditionallyProcessAgentRequests([
          {
            action,
            input,
          },
        ]);
      } else if (action === 'add_secrets') {
        const input = agentAddSecretsRequestModel.parse(event.data.data);
        void conditionallyProcessAgentRequests([
          {
            action,
            input,
          },
        ]);
      } else {
        unreachable(action);
      }
    } catch (error) {
      console.error(`Unable to handle message in onIframePostMessage()`, error);
    }
  };

  useEffect(() => {
    if (currentEntry && wallet) {
      try {
        const rawInput = localStorage.getItem(PENDING_TRANSACTION_KEY);
        if (rawInput) {
          const request: AgentRequestWithPermissions = {
            action: 'near_send_transactions',
            input: JSON.parse(rawInput) as z.infer<
              typeof agentNearSendTransactionsRequestModel
            >,
          };
          void conditionallyProcessAgentRequests([request], true);
        }
      } catch (error) {
        console.error(error);
      }

      localStorage.removeItem(PENDING_TRANSACTION_KEY);
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentEntry, wallet]);

  useEffect(() => {
    if (queryParams.transactionHashes) {
      handleWalletTransactionResponse({
        result: queryParams.transactionHashes,
        requestId: queryParams.transactionRequestId,
      });
    }
  }, [queryParams, handleWalletTransactionResponse]);

  return {
    agentRequestsNeedingPermissions,
    conditionallyProcessAgentRequests,
    iframeNonce,
    iframePostMessage,
    onIframePostMessage,
    setAgentRequestsNeedingPermissions,
  };
}
