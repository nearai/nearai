'use client';

import { handleClientError } from '@near-pagoda/ui';
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
  const setAuth = useAuthStore((store) => store.setAuth);
  const clearAuth = useAuthStore((store) => store.clearAuth);
  const router = useRouter();

  const testMutation = trpc.auth.test.useMutation();
  // const testQuery = trpc.auth.testQuery.useQuery();

  useEffect(() => {
    setTimeout(() => {
      testMutation.mutate();
    }, 1000);
  }, []);

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

        await saveTokenMutation.mutateAsync(auth);

        setAuth(auth);

        // router.replace(returnUrlToRestoreAfterSignIn());
      } catch (error) {
        handleClientError({
          error,
          title: 'Invalid Token',
          description: 'Please try signing in again',
        });

        clearAuth();
      }
    }

    void signIn();
  }, [currentNonce, router, saveTokenMutation, clearAuth, setAuth]);

  return null;
}
