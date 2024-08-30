'use client';

import { Gear } from '@phosphor-icons/react';

import { Flex } from '~/components/lib/Flex';
import { Section } from '~/components/lib/Section';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Text } from '~/components/lib/Text';
import { SignInPromptSection } from '~/components/SignInPrompt';
import { useAuthStore } from '~/stores/auth';

import { NonceList } from './NonceList';

export default function SettingsPage() {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);

  return (
    <>
      <Section background="sand-2">
        <Flex align="center" gap="m">
          <SvgIcon icon={<Gear weight="thin" />} size="l" />
          <Text as="h1">Settings</Text>
        </Flex>
      </Section>

      {isAuthenticated ? (
        <Section>
          <NonceList />
        </Section>
      ) : (
        <SignInPromptSection />
      )}
    </>
  );
}
