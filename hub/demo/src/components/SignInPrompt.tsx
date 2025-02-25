'use client';

import { Button, Container, Flex, Section, Text } from '@near-pagoda/ui';
import { ArrowRight } from '@phosphor-icons/react';

import { signIn } from '~/lib/auth';

type Props = {
  layout?: 'horizontal-right' | 'horizontal-justified';
};

export const SignInPrompt = ({ layout = 'horizontal-right' }: Props) => {
  return (
    <Flex
      gap="m"
      align="center"
      justify={layout === 'horizontal-right' ? 'end' : 'space-between'}
    >
      <Text size="text-s">Please sign in to continue</Text>
      <Button
        variant="affirmative"
        label="Sign In"
        onClick={signIn}
        size="small"
        iconRight={<ArrowRight />}
      />
    </Flex>
  );
};

export const SignInPromptSection = () => {
  return (
    <Section grow="available">
      <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
        <Flex direction="column" gap="m" align="center">
          <Text size="text-l">Welcome</Text>
          <Text>Please sign in to continue</Text>
          <Button
            variant="affirmative"
            label="Sign In"
            onClick={signIn}
            size="large"
            iconRight={<ArrowRight />}
          />
        </Flex>
      </Container>
    </Section>
  );
};
