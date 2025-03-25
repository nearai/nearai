import { handleClientError } from '@nearai/ui';
import { z } from 'zod';

import { env } from '@/env';
import { useAuthStore } from '@/stores/auth';
import { clientUtils } from '@/trpc/TRPCProvider';
import { getHashParams } from '@/utils/url';

const AUTH_NEAR_URL = env.NEXT_PUBLIC_AUTH_URL;

export const RECIPIENT = 'ai.near';
export const MESSAGE = 'Welcome to NEAR AI Hub!';
export const REVOKE_MESSAGE = 'Are you sure? Revoking a nonce';
export const REVOKE_ALL_MESSAGE = 'Are you sure? Revoking all nonces';
export const SIGN_IN_CALLBACK_PATH = '/sign-in/callback';
export const SIGN_IN_RESTORE_URL_KEY = 'signInRestoreUrl';
const SIGN_IN_NONCE_KEY = 'signInNonce';

const authenticatedPostMessageModel = z.object({
  authenticated: z.boolean(),
});

const myNearWalletPostMessageModel = z.object({
  status: z.literal('success'),
  accountUrlCallbackUrl: z.string().url(),
  signedRequest: z.object({
    accountId: z.string(),
    signature: z.string(),
    publicKey: z.string(),
  }),
});

export function signIn() {
  const nonce = generateNonce();

  localStorage.setItem(
    SIGN_IN_RESTORE_URL_KEY,
    `${location.pathname}${location.search}`,
  );

  localStorage.setItem(SIGN_IN_NONCE_KEY, nonce);

  setTimeout(() => {
    openAuthUrl(MESSAGE, RECIPIENT, nonce, returnSignInCallbackUrl());
  }, 10);
}

export function returnSignInNonce() {
  return localStorage.getItem(SIGN_IN_NONCE_KEY);
}

export function clearSignInNonce() {
  return localStorage.removeItem(SIGN_IN_NONCE_KEY);
}

export function returnSignInCallbackUrl() {
  return location.origin + SIGN_IN_CALLBACK_PATH;
}

export function returnUrlToRestoreAfterSignIn() {
  const url = localStorage.getItem(SIGN_IN_RESTORE_URL_KEY) || '/';
  if (url.startsWith(SIGN_IN_CALLBACK_PATH)) return '/';
  return url;
}

export function createAuthUrl(
  message: string,
  recipient: string,
  nonce: string,
  callbackUrl: string,
) {
  const urlParams = new URLSearchParams({
    message,
    recipient,
    nonce,
    callbackUrl,
  });

  return `${AUTH_NEAR_URL}/?${urlParams.toString()}`;
}

export function openAuthUrl(
  message: string,
  recipient: string,
  nonce: string,
  callbackUrl: string,
) {
  const url = createAuthUrl(message, recipient, nonce, callbackUrl);

  const width = 775;
  const height = 775;
  const left = screen.width / 2 - width / 2;
  const top = screen.height / 2 - height / 2;

  const popup = window.open(
    url,
    '_blank',
    `popup=yes,scrollbars=yes,resizable=yes,width=${width},height=${height},left=${left},top=${top}`,
  );

  if (popup) {
    async function postMessageEventHandler(event: MessageEvent) {
      if (!popup) return;
      const data = event.data as Record<string, unknown>;
      const parsed = z
        .union([myNearWalletPostMessageModel, authenticatedPostMessageModel])
        .safeParse(data);
      if (!parsed.data) return;

      if ('signedRequest' in parsed.data) {
        /*
          MyNearWallet has baked in logic that checks for the existence of window.opener:
          https://github.com/mynearwallet/my-near-wallet/blob/master/packages/frontend/src/routes/SignWrapper.js#L108

          This forces us to listen for their postMessage() event and execute the expected 
          redirect back to our defined callbackUrl.
        */

        const { signedRequest } = parsed.data;
        const urlParams = new URLSearchParams({
          signature: signedRequest.signature,
          accountId: signedRequest.accountId,
          publicKey: signedRequest.publicKey,
          signedMessageParams: JSON.stringify({
            message,
            recipient,
            callbackUrl,
            nonce,
          }),
        });
        popup.location.href = `${callbackUrl}#${urlParams.toString()}`;
      } else if (parsed.data.authenticated) {
        const { setAuth, clearAuth } = useAuthStore.getState();
        try {
          const auth = await clientUtils.auth.getSession.fetch();
          await clientUtils.invalidate();
          if (!auth) throw new Error('Failed to return current auth session');
          setAuth(auth);
          popup.close();
          window.focus();
        } catch (error) {
          clearAuth();
          handleClientError({ error, title: 'Failed to sign in' });
        }
      }
    }

    popup.focus();
    window.addEventListener('message', postMessageEventHandler);

    const interval = setInterval(() => {
      if (popup?.closed) {
        window.removeEventListener('message', postMessageEventHandler);
        clearInterval(interval);
      }
    }, 500);
  }
}

/**
 * Generates a nonce, which is current time in milliseconds
 * and pads it with zeros to ensure it is exactly 32 bytes in length.
 */
export function generateNonce() {
  const nonce = Date.now().toString();
  return nonce.padStart(32, '0');
}

export function extractSignatureFromHashParams() {
  const hashParams = getHashParams(location.hash);

  if (!hashParams.signature) {
    return null;
  }

  const accountId = hashParams.accountId;
  const publicKey = hashParams.publicKey;
  const signature = hashParams.signature;
  let nonce = hashParams.nonce || returnSignInNonce();

  if (hashParams.signedMessageParams) {
    try {
      const signedMessageParams = JSON.parse(
        hashParams.signedMessageParams,
      ) as Record<string, string>;
      if (signedMessageParams.nonce) {
        nonce = signedMessageParams.nonce;
      }
    } catch (error) {
      console.error(
        'Failed to parse stringified JSON: signedMessageParams',
        error,
      );
    }
  }

  return { accountId, publicKey, signature, nonce };
}
