'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import {
  extractSignatureFromHashParams,
  MESSAGE,
  RECIPIENT,
  returnUrlToRestoreAfterSignIn,
  SIGN_IN_CALLBACK_URL,
} from '~/lib/auth';
import { authorizationModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';

export default function SignInCallbackPage() {
  const currentNonce = useAuthStore((store) => store.currentNonce);
  const clearAuth = useAuthStore((store) => store.clearAuth);
  const setAuthRaw = useAuthStore((store) => store.setAuthRaw);
  const router = useRouter();

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const hashParams = extractSignatureFromHashParams();

    if (hashParams && currentNonce) {
      try {
        const auth = authorizationModel.parse({
          account_id: hashParams.accountId,
          public_key: hashParams.publicKey,
          signature: hashParams.signature,
          callback_url: SIGN_IN_CALLBACK_URL,
          message: MESSAGE,
          recipient: RECIPIENT,
          nonce: currentNonce,
        });

        setAuthRaw(`Bearer ${JSON.stringify(auth)}`);

        const url = returnUrlToRestoreAfterSignIn();
        router.replace(url);
      } catch (error) {
        console.error(error);
        clearAuth();
      }
    }
  }, [currentNonce, clearAuth, router, setAuthRaw]);

  return null;
}
