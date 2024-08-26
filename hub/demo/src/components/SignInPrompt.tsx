'use client';

import { ArrowRight } from '@phosphor-icons/react';

import { signInWithNear } from '~/lib/auth';

import { Button } from './lib/Button';
import { Card } from './lib/Card';
import { Container } from './lib/Container';
import { Text } from './lib/Text';

export const SignInPrompt = () => {
  return (
    <Container size="xs" style={{ margin: 'auto' }}>
      <Card padding="l" style={{ textAlign: 'center' }}>
        <Text size="text-l">Welcome</Text>
        <Text>Please sign in with your NEAR wallet to continue</Text>
        <Button
          variant="affirmative"
          label="Sign In"
          onClick={signInWithNear}
          size="large"
          iconRight={<ArrowRight />}
        />
      </Card>
    </Container>
  );
};
