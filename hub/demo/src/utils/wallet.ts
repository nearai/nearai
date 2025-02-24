import { type AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

export type WalletTransactionRequestOrigin = 'iframe' | 'quote';

export const WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS = [
  'transactionHashes',
  'transactionRequestId',
  'transactionRequestOrigin',
] as const;

export type WalletTransactionCallbackUrlQueryParam =
  (typeof WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS)[number];

export const UNSET_WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS: Record<
  WalletTransactionCallbackUrlQueryParam,
  null
> = {
  transactionHashes: null,
  transactionRequestId: null,
  transactionRequestOrigin: null,
};

export function generateWalletTransactionCallbackUrl(
  requestOrigin: WalletTransactionRequestOrigin,
  requestId?: string | null,
) {
  const callbackUrl = new URL(window.location.href);

  callbackUrl.searchParams.set(
    'transactionRequestOrigin' satisfies WalletTransactionCallbackUrlQueryParam,
    requestOrigin,
  );

  if (requestId) {
    callbackUrl.searchParams.set(
      'transactionRequestId' satisfies WalletTransactionCallbackUrlQueryParam,
      requestId,
    );
  }

  return callbackUrl.toString();
}

export function resetWalletTransactionCallbackUrlQueryParams(
  router: AppRouterInstance,
) {
  const callbackUrl = new URL(window.location.href);

  WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS.forEach((queryParam) => {
    callbackUrl.searchParams.delete(queryParam);
  });

  router.replace(callbackUrl.pathname + callbackUrl.search, { scroll: false });
}
