import { env } from '~/env';
import { getHashParams } from '~/utils/url';

const AUTH_NEAR_URL = env.NEXT_PUBLIC_AUTH_URL;

export const RECIPIENT = 'ai.near';
export const MESSAGE = 'Welcome to NEAR AI Hub!';
export const REVOKE_MESSAGE = 'Are you sure? Revoking a nonce';
export const REVOKE_ALL_MESSAGE = 'Are you sure? Revoking all nonces';
export const SIGN_IN_CALLBACK_PATH = '/sign-in/callback';
const SIGN_IN_RESTORE_URL_KEY = 'signInRestoreUrl';
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
  window.location.href = url;
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
