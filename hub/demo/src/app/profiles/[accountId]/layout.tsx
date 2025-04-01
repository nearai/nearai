'use client';

import {
  Badge,
  Flex,
  ImageIcon,
  Section,
  SvgIcon,
  Tabs,
  Text,
} from '@nearai/ui';
import { Cube, Star, User } from '@phosphor-icons/react';
import { usePathname } from 'next/navigation';
import { type ReactNode } from 'react';

import { useProfileParams } from '@/hooks/profile';
import { useAuthStore } from '@/stores/auth';

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathSegments = usePathname().split('/');
  const { accountId } = useProfileParams();
  const auth = useAuthStore((store) => store.auth);
  let activeTab: 'published' | 'starred' = 'published';
  const baseUrl = `/profiles/${accountId}`;

  if (pathSegments.at(-1) === 'starred') {
    activeTab = 'starred';
  }

  return (
    <>
      <Section background="sand-0" bleed gap="m" tabs>
        <Flex align="center" gap="m">
          <ImageIcon
            size="l"
            src={undefined}
            alt={accountId}
            fallbackIcon={<User />}
          />
          {/* NOTE: At some point we should have actual avatars for users... */}

          <Text as="h1" size="text-l">
            {accountId}
          </Text>

          {auth?.accountId === accountId && (
            <Badge label="You" variant="neutral" />
          )}
        </Flex>

        <Tabs.Root value={activeTab}>
          <Tabs.List>
            <Tabs.Trigger href={`${baseUrl}`} value="published">
              <SvgIcon icon={<Cube fill="bold" />} />
              Published
            </Tabs.Trigger>

            <Tabs.Trigger href={`${baseUrl}/starred`} value="starred">
              <SvgIcon icon={<Star fill="bold" />} />
              Starred
            </Tabs.Trigger>
          </Tabs.List>
        </Tabs.Root>
      </Section>

      {children}
    </>
  );
}
