'use client';

import { ArrowRight } from '@phosphor-icons/react';

import { signInWithNear } from '~/lib/auth';

import { Button } from './lib/Button';
import { Container } from './lib/Container';
import { Flex } from './lib/Flex';
import { Section } from './lib/Section';
import { Text } from './lib/Text';

export const SignInPrompt = () => {
  return (
    <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
      <Flex direction="column" gap="m" align="center">
        <Text size="text-l">Welcome</Text>
        <Text>Please sign in with your NEAR wallet to continue</Text>
        <Button
          variant="affirmative"
          label="Sign In"
          onClick={signInWithNear}
          size="large"
          iconRight={<ArrowRight />}
        />
      </Flex>
    </Container>
  );
};

export const SignInPromptSection = () => {
  return (
    <Section grow="available">
      <SignInPrompt />
    </Section>
  );
};
