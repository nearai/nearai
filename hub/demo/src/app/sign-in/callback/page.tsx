'use client';

import {
  Button,
  Container,
  Flex,
  handleClientError,
  Section,
  Text,
} from '@nearai/ui';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { type z } from 'zod';

import {
  extractSignatureFromHashParams,
  MESSAGE,
  RECIPIENT,
  returnSignInCallbackUrl,
  returnUrlToRestoreAfterSignIn,
  signIn,
} from '@/lib/auth';
import { authorizationModel } from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { trpc } from '@/trpc/TRPCProvider';

export default function SignInCallbackPage() {
  const saveTokenMutation = trpc.auth.saveToken.useMutation();
  const router = useRouter();
  const [parsedAuth, setParsedAuth] = useState<z.infer<
    typeof authorizationModel
  > | null>(null);
  const [isInvalidToken, setIsInvalidToken] = useState(false);

  useEffect(() => {
    async function parseToken() {
      try {
        const hashParams = extractSignatureFromHashParams();

        const auth = authorizationModel.parse({
          account_id: hashParams?.accountId,
          public_key: hashParams?.publicKey,
          signature: hashParams?.signature,
          callback_url: returnSignInCallbackUrl(),
          message: MESSAGE,
          recipient: RECIPIENT,
          nonce: hashParams?.nonce,
        });

        setParsedAuth(auth);
      } catch (error) {
        console.error(error);
        setIsInvalidToken(true);
      }
    }

    void parseToken();
  }, []);

  useEffect(() => {
    if (!parsedAuth) return;
    if (!saveTokenMutation.isIdle) return;

    saveTokenMutation.mutate(parsedAuth, {
      onSuccess: () => {
        const opener = window.opener as WindowProxy | null;

        if (opener) {
          opener.postMessage(
            {
              authenticated: true,
            },
            '*',
          );
        } else {
          const { setAuth } = useAuthStore.getState();
          setAuth({
            accountId: parsedAuth.account_id,
          });
          router.replace(returnUrlToRestoreAfterSignIn());
        }
      },
      onError: (error) => {
        const { clearAuth } = useAuthStore.getState();
        clearAuth();
        handleClientError({ error });
      },
    });
  }, [parsedAuth, saveTokenMutation, router]);

  return (
    <Section grow="available">
      <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
        <Flex direction="column" gap="l" align="center">
          {isInvalidToken ? (
            <>
              <Text color="red-10">
                Your token is invalid. Please try signing in again.
              </Text>

              <Button label="Sign In" onClick={() => signIn()} />
            </>
          ) : (
            <>
              <Text color="sand-10">Verifying...</Text>
              <Button label="Sign In" loading fill="ghost" />
            </>
          )}
        </Flex>
      </Container>
    </Section>
  );
}
