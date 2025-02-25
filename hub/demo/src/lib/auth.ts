import { env } from '~/env';
import { useAuthStore } from '~/stores/auth';
import { getHashParams } from '~/utils/url';

import { authorizationModel } from './models';

const AUTH_NEAR_URL = env.NEXT_PUBLIC_AUTH_URL;

export const RECIPIENT = 'ai.near';
export const MESSAGE = 'Welcome to NEAR AI Hub!';
export const REVOKE_MESSAGE = 'Are you sure? Revoking a nonce';
export const REVOKE_ALL_MESSAGE = 'Are you sure? Revoking all nonces';
export const SIGN_IN_CALLBACK_PATH = '/sign-in/callback';
export const SIGN_IN_RESTORE_URL_KEY = 'signInRestoreUrl';
const SIGN_IN_NONCE_KEY = 'signInNonce';

export function signInWithNear() {
  const nonce = generateNonce();

  localStorage.setItem(
    SIGN_IN_RESTORE_URL_KEY,
    `${location.pathname}${location.search}`,
  );

  localStorage.setItem(SIGN_IN_NONCE_KEY, nonce);

  setTimeout(() => {
    redirectToAuthNearLink(
      MESSAGE,
      RECIPIENT,
      nonce,
      returnSignInCallbackUrl(),
    );
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

export function createAuthNearLink(
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

export function redirectToAuthNearLink(
  message: string,
  recipient: string,
  nonce: string,
  callbackUrl: string,
) {
  const url = createAuthNearLink(message, recipient, nonce, callbackUrl);

  const width = 400;
  const height = 600;
  const left = screen.width / 2 - width / 2;
  const top = screen.height / 2 - height / 2;

  const popup = window.open(
    url,
    '_blank',
    `popup=yes,scrollbars=yes,resizable=yes,width=${width},height=${height},left=${left},top=${top}`,
  );

  if (popup) {
    popup.focus();

    window.addEventListener('message', (event) => {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      const parsed = authorizationModel.safeParse(event.data?.auth);
      const auth = parsed.data;

      if (auth) {
        const setAuth = useAuthStore.getState().setAuth;
        setAuth(auth);
        popup.close();
      }
    });
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
  let nonce = returnSignInNonce();

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
