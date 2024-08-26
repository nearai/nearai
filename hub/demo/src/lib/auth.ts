import { env } from '~/env';
import { parseHashParams } from '~/hooks/misc';
import { useAuthStore } from '~/stores/auth';

export const CALLBACK_URL = env.NEXT_PUBLIC_BASE_URL;
export const RECIPIENT = 'ai.near';
export const MESSAGE = 'Welcome to NEAR AI Hub!';
export const REVOKE_MESSAGE = 'Are you sure? Revoking a nonce';
export const REVOKE_ALL_MESSAGE = 'Are you sure? Revoking all nonces';

export function signInWithNear() {
  const nonce = generateNonce();
  useAuthStore.setState({
    currentNonce: nonce,
  });
  redirectToAuthNearLink(MESSAGE, RECIPIENT, nonce, location.href);
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

  return `https://auth.near.ai/?${urlParams.toString()}`;
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
  const hashParams = parseHashParams(location.hash);

  if (!hashParams.signature) {
    return null;
  }

  const accountId = hashParams.accountId;
  const publicKey = hashParams.publicKey;
  const signature = hashParams.signature;

  return { accountId, publicKey, signature };
}
