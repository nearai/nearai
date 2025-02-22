'use client';

import { Button, Container, Flex, Section, Text } from '@near-pagoda/ui';
import { ArrowRight } from '@phosphor-icons/react';

import { useIsEmbeddedIframe } from '~/hooks/embed';
import { signInWithNear } from '~/lib/auth';

type Props = {
  layout?: 'horizontal-right' | 'horizontal-justified';
};

export const SignInPrompt = ({ layout = 'horizontal-right' }: Props) => {
  const { isEmbedded } = useIsEmbeddedIframe();

  return (
    <Flex
      gap="m"
      align="center"
      justify={layout === 'horizontal-right' ? 'end' : 'space-between'}
    >
      <Text size="text-s">Please sign in to continue</Text>
      {!isEmbedded && (
        <Button
          variant="affirmative"
          label="Sign In"
          onClick={signInWithNear}
          size="small"
          iconRight={<ArrowRight />}
        />
      )}
    </Flex>
  );
};

export const SignInPromptSection = () => {
  const { isEmbedded } = useIsEmbeddedIframe();

  return (
    <Section grow="available">
      <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
        <Flex direction="column" gap="m" align="center">
          <Text size="text-l">Welcome</Text>
          <Text>Please sign in to continue</Text>
          {!isEmbedded && (
            <Button
              variant="affirmative"
              label="Sign In"
              onClick={signInWithNear}
              size="large"
              iconRight={<ArrowRight />}
            />
          )}
        </Flex>
      </Container>
    </Section>
  );
};
