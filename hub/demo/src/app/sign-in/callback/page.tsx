'use client';

import {
  Button,
  Container,
  Flex,
  handleClientError,
  Section,
  Text,
} from '@near-pagoda/ui';
import { ArrowRight } from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { type z } from 'zod';

import {
  extractSignatureFromHashParams,
  MESSAGE,
  RECIPIENT,
  returnSignInCallbackUrl,
  returnSignInNonce,
  returnUrlToRestoreAfterSignIn,
  signInWithNear,
} from '~/lib/auth';
import { authorizationModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { trpc } from '~/trpc/TRPCProvider';

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
        const nonce = returnSignInNonce();

        const auth = authorizationModel.parse({
          account_id: hashParams?.accountId,
          public_key: hashParams?.publicKey,
          signature: hashParams?.signature,
          callback_url: returnSignInCallbackUrl(),
          message: MESSAGE,
          recipient: RECIPIENT,
          nonce,
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
        const { setAuth } = useAuthStore.getState();
        setAuth(parsedAuth);
        router.replace(returnUrlToRestoreAfterSignIn());
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

              <Button
                variant="affirmative"
                label="Sign In"
                onClick={() => signInWithNear()}
                iconRight={<ArrowRight />}
              />
            </>
          ) : (
            <>
              <Text color="sand-10">Verifying...</Text>
              <Button icon={<></>} label="Sign In" loading fill="ghost" />
            </>
          )}
        </Flex>
      </Container>
    </Section>
  );
}
