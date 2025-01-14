'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import {
  extractSignatureFromHashParams,
  MESSAGE,
  RECIPIENT,
  returnSignInCallbackUrl,
  returnUrlToRestoreAfterSignIn,
} from '~/lib/auth';
import { authorizationModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { trpc } from '~/trpc/TRPCProvider';

export default function SignInCallbackPage() {
  const saveTokenMutation = trpc.auth.saveToken.useMutation();
  const currentNonce = useAuthStore((store) => store.currentNonce);
  // const clearAuth = useAuthStore((store) => store.clearAuth);
  // const setAuthRaw = useAuthStore((store) => store.setAuthRaw);
  const router = useRouter();

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!saveTokenMutation.isIdle) return;

    async function signIn() {
      try {
        const hashParams = extractSignatureFromHashParams();
        if (!hashParams || !currentNonce) return;

        const auth = authorizationModel.parse({
          account_id: hashParams.accountId,
          public_key: hashParams.publicKey,
          signature: hashParams.signature,
          callback_url: returnSignInCallbackUrl(),
          message: MESSAGE,
          recipient: RECIPIENT,
          nonce: currentNonce,
        });

        // setAuthRaw(`Bearer ${JSON.stringify(auth)}`);

        await saveTokenMutation.mutateAsync(auth);

        const url = returnUrlToRestoreAfterSignIn();
        console.log(url);
        // router.replace(url);
      } catch (error) {
        console.error(error);
        // clearAuth(); TODO
      }
    }

    void signIn();
  }, [currentNonce, router, saveTokenMutation]);

  return null;
}
