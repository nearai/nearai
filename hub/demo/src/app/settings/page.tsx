'use client';

import { Flex, Section, SvgIcon, Text } from '@near-pagoda/ui';
import { Gear } from '@phosphor-icons/react';

import { SignInPromptSection } from '~/components/SignInPrompt';
import { useAuthStore } from '~/stores/auth';

export default function SettingsPage() {
  const auth = useAuthStore((store) => store.auth);

  return (
    <>
      <Section background="sand-2">
        <Flex align="center" gap="m">
          <SvgIcon icon={<Gear weight="thin" />} size="l" />
          <Text as="h1">Settings</Text>
        </Flex>
      </Section>

      {auth ? (
        <Section>
          <Text>Coming soon...</Text>
        </Section>
      ) : (
        <SignInPromptSection />
      )}
    </>
  );
}
