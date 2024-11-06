import { type FinalExecutionOutcome } from '@near-wallet-selector/core';
import { type UseMutationResult } from '@tanstack/react-query';
import { formatNearAmount } from 'near-api-js/lib/utils/format';
import { useCallback, useEffect, useState } from 'react';
import { type z } from 'zod';

import {
  type AgentRequest,
  checkAgentPermissions,
} from '~/components/AgentPermissionsModal';
import { type AgentChatMutationInput } from '~/components/AgentRunner';
import { type IframePostMessageEventHandler } from '~/components/lib/IframeWithBlob';
import {
  agentWalletAccountRequestModel,
  agentWalletTransactionsRequestModel,
  agentWalletViewRequestModel,
  chatWithAgentModel,
  type entryModel,
} from '~/lib/models';
import { useNearStore } from '~/stores/near';
import { useWalletStore } from '~/stores/wallet';
import { api } from '~/trpc/react';
import { unreachable } from '~/utils/unreachable';

import { useQueryParams } from './url';

const PENDING_TRANSACTION_KEY = 'agent-transaction-request-pending-connection';

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
  const [agentRequestsNeedingPermissions, setAgentRequestsNeedingPermissions] =
    useState<AgentRequest[] | null>(null);
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
    requests: AgentRequest[],
    allowedBypass?: boolean,
  ) => {
    if (!currentEntry) return;

    const permissionsCheck = checkAgentPermissions(currentEntry, requests);

    if (allowedBypass ?? permissionsCheck.allowed) {
      requests.forEach(async (request) => {
        if ('agent_id' in request) {
          await chatMutation.mutateAsync(request);
        } else {
          if (wallet) {
            try {
              const callbackUrl = new URL(window.location.href);
              if (request.requestId) {
                callbackUrl.searchParams.set(
                  'transactionRequestId',
                  request.requestId,
                );
              }

              const result = await wallet.signAndSendTransactions({
                transactions: request.transactions,
                callbackUrl: callbackUrl.toString(),
              });

              if (result) {
                handleWalletTransactionResponse({
                  result,
                  requestId: request.requestId,
                });
              }
            } catch (error) {
              console.error(error);
            }
          } else {
            localStorage.setItem(
              PENDING_TRANSACTION_KEY,
              JSON.stringify(request),
            );
            walletSignInModal!.show();
          }
        }
      });
    } else {
      setAgentRequestsNeedingPermissions(requests);
    }
  };

  const onIframePostMessage: IframePostMessageEventHandler<{
    action:
      | 'near_account'
      | 'near_send_transactions'
      | 'near_view'
      | 'remote_agent_run'
      | 'refresh_thread_id';
    data: unknown;
  }> = async (event) => {
    try {
      const action = event.data.action;

      if (action === 'near_send_transactions') {
        const request = agentWalletTransactionsRequestModel.parse(
          event.data.data,
        );
        void conditionallyProcessAgentRequests([request]);
      } else if (action === 'near_view') {
        const request = agentWalletViewRequestModel.parse(event.data.data);
        const result: unknown = await nearViewAccount!.viewFunction(request);
        setIframePostMessage({
          action: 'near_view_response',
          requestId: request.requestId,
          result,
        });
      } else if (action === 'near_account') {
        const request = agentWalletAccountRequestModel.parse(event.data.data);

        let accountId = request.accountId;

        if (!accountId && selector) {
          // get current accountId
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
            requestId: request.requestId,
            result: { accountId, balance: NEAR, yNEAR },
          });
        } else {
          console.error('Missing data read `near_account`');
        }
      } else if (action === 'refresh_thread_id') {
        const chat = chatWithAgentModel.partial().parse(event.data.data);
        if (chat.thread_id) {
          void utils.hub.thread.invalidate({ threadId: chat.thread_id });
          updateQueryPath({ threadId: chat.thread_id }, 'replace', false);
        }
      } else if (action === 'remote_agent_run') {
        const chat = chatWithAgentModel.parse(event.data.data);
        chat.max_iterations = Number(chat.max_iterations) || 1;
        chat.thread_id = chat.thread_id ?? threadId;
        void conditionallyProcessAgentRequests([chat]);
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
        const rawRequest = localStorage.getItem(PENDING_TRANSACTION_KEY);
        if (rawRequest) {
          const request = JSON.parse(rawRequest) as AgentRequest;
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
    iframePostMessage,
    onIframePostMessage,
    setAgentRequestsNeedingPermissions,
  };
}
