import { useEffect } from 'react';

import { parseHashParams } from '~/hooks/misc';
import { CALLBACK_URL, MESSAGE, RECIPIENT } from '~/lib/auth';
import { authorizationModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';

/**
 * This hook is used to handle the login process
 * It will parse the hash params from the url, and set the auth value in the store
 */
export function useHandleSignIn() {
  const store = useAuthStore();

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const hashParams = parseHashParams(location.hash);

    if (hashParams.signature && store.currentNonce) {
      try {
        const auth = authorizationModel.parse({
          account_id: hashParams.accountId,
          public_key: hashParams.publicKey,
          signature: hashParams.signature,
          callback_url: CALLBACK_URL,
          message: MESSAGE,
          recipient: RECIPIENT,
          nonce: store.currentNonce,
        });

        store.setAuthRaw(`Bearer ${JSON.stringify(auth)}`);

        // cleanup url
        window.history.replaceState(
          null,
          '',
          window.location.pathname + window.location.search,
        );
      } catch (error) {
        console.error(error);
        store.clearAuth();
      }
    }
  }, [store]);
}
