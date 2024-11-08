import { env } from '~/env';
import { useAuthStore } from '~/stores/auth';
import { getHashParams } from '~/utils/url';

const AUTH_NEAR_URL = env.NEXT_PUBLIC_AUTH_URL;

export const RECIPIENT = 'ai.near';
export const MESSAGE = 'Welcome to NEAR AI Hub!';
export const REVOKE_MESSAGE = 'Are you sure? Revoking a nonce';
export const REVOKE_ALL_MESSAGE = 'Are you sure? Revoking all nonces';
const SIGN_IN_RESTORE_URL_KEY = 'signInRestoreUrl';

export function signInWithNear() {
  const nonce = generateNonce();

  localStorage.setItem(
    SIGN_IN_RESTORE_URL_KEY,
    `${location.pathname}${location.search}`,
  );

  useAuthStore.setState({
    currentNonce: nonce,
  });

  redirectToAuthNearLink(MESSAGE, RECIPIENT, nonce, returnSignInCallbackUrl());
}

export function returnSignInCallbackUrl() {
  return location.origin + '/sign-in/callback';
}

export function returnUrlToRestoreAfterSignIn() {
  const url = localStorage.getItem(SIGN_IN_RESTORE_URL_KEY) || '/';
  if (url === '/sign-in/callback') return '/';
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
  window.location.replace(url);
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

  return { accountId, publicKey, signature };
}
