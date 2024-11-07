'use client';

import { useTheme } from '@near-pagoda/ui';
import {
  BreakpointDisplay,
  Button,
  Dropdown,
  Flex,
  SvgIcon,
  Text,
  Tooltip,
} from '@near-pagoda/ui';
import {
  BookOpenText,
  ChatCircleDots,
  Cube,
  Gear,
  List,
  Moon,
  Star,
  Sun,
  User,
  X,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { env } from '~/env';
import { signInWithNear } from '~/lib/auth';
import { ENTRY_CATEGORY_LABELS } from '~/lib/entries';
import { useAuthStore } from '~/stores/auth';
import { useWalletStore } from '~/stores/wallet';

import s from './Navigation.module.scss';

const navItems = [
  {
    label: 'Agents',
    path: '/agents',
    icon: ENTRY_CATEGORY_LABELS.agent.icon,
    consumer: true,
  },
  {
    label: 'Models',
    path: '/models',
    icon: ENTRY_CATEGORY_LABELS.model.icon,
    consumer: false,
  },
  {
    label: 'Datasets',
    path: '/datasets',
    icon: ENTRY_CATEGORY_LABELS.dataset.icon,
    consumer: false,
  },
  {
    label: 'Benchmarks',
    path: '/benchmarks',
    icon: ENTRY_CATEGORY_LABELS.benchmark.icon,
    consumer: false,
  },
  {
    label: 'Evaluations',
    path: '/evaluations',
    icon: ENTRY_CATEGORY_LABELS.evaluation.icon,
    consumer: false,
  },
  {
    label: 'Chat',
    path: '/chat',
    icon: <ChatCircleDots />,
    consumer: true,
  },
].filter((item) => !env.NEXT_PUBLIC_CONSUMER_MODE || item.consumer);

export const Navigation = () => {
  const auth = useAuthStore((store) => store.auth);
  const clearAuth = useAuthStore((store) => store.clearAuth);
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const wallet = useWalletStore((store) => store.wallet);
  const path = usePathname();
  const [mounted, setMounted] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();

  const title = env.NEXT_PUBLIC_CONSUMER_MODE ? 'AI Chat' : 'AI Hub';

  useEffect(() => {
    setMounted(true);
  }, []);

  const signOut = () => {
    if (wallet) {
      void wallet.signOut();
    }

    clearAuth();
  };

  return (
    <header className={s.navigation}>
      <Link className={s.logo} href="/">
        {title}
      </Link>

      <BreakpointDisplay show="larger-than-tablet" className={s.breakpoint}>
        <Flex align="center" gap="m">
          {navItems.map((item) => (
            <Link
              className={s.item}
              href={item.path}
              key={item.path}
              data-active={path.startsWith(item.path)}
            >
              {item.label}
            </Link>
          ))}
        </Flex>
      </BreakpointDisplay>

      <Flex align="center" gap="m" style={{ marginLeft: 'auto' }}>
        <Flex align="center" gap="xs">
          {mounted && resolvedTheme === 'dark' ? (
            <Tooltip asChild content="Switch to light mode">
              <Button
                label="Switch to light mode"
                size="small"
                icon={<Moon weight="duotone" />}
                fill="ghost"
                onClick={() => setTheme('light')}
              />
            </Tooltip>
          ) : (
            <Tooltip asChild content="Switch to dark mode">
              <Button
                label="Switch to dark mode"
                size="small"
                icon={<Sun weight="duotone" />}
                fill="ghost"
                onClick={() => setTheme('dark')}
              />
            </Tooltip>
          )}

          <Tooltip asChild content="View Documentation">
            <Button
              label="View Documentation"
              size="small"
              icon={<BookOpenText weight="duotone" />}
              fill="ghost"
              href="https://docs.near.ai"
              target="_blank"
            />
          </Tooltip>
        </Flex>

        <BreakpointDisplay show="smaller-than-desktop" className={s.breakpoint}>
          <Dropdown.Root>
            <Dropdown.Trigger asChild>
              <Button
                label="Navigation"
                size="small"
                fill="outline"
                variant="secondary"
                icon={<List weight="bold" />}
              />
            </Dropdown.Trigger>

            <Dropdown.Content>
              <Dropdown.Section>
                {navItems.map((item) => (
                  <Dropdown.Item href={item.path} key={item.path}>
                    <SvgIcon icon={item.icon} />
                    {item.label}
                  </Dropdown.Item>
                ))}
              </Dropdown.Section>
            </Dropdown.Content>
          </Dropdown.Root>
        </BreakpointDisplay>

        {isAuthenticated ? (
          <Dropdown.Root>
            <Dropdown.Trigger asChild>
              <Button
                label="User Settings"
                size="small"
                icon={<User weight="bold" />}
              />
            </Dropdown.Trigger>

            <Dropdown.Content style={{ width: '12rem' }}>
              <Dropdown.Section>
                <Dropdown.SectionContent>
                  <Text
                    size="text-xs"
                    weight={600}
                    color="sand-12"
                    clampLines={1}
                  >
                    {auth?.account_id}
                  </Text>
                </Dropdown.SectionContent>
              </Dropdown.Section>

              <Dropdown.Section>
                <Dropdown.Item href={`/profiles/${auth?.account_id}`}>
                  <SvgIcon icon={<Cube />} />
                  Your Work
                </Dropdown.Item>

                <Dropdown.Item href={`/profiles/${auth?.account_id}/starred`}>
                  <SvgIcon icon={<Star />} />
                  Your Stars
                </Dropdown.Item>

                <Dropdown.Item href="/settings">
                  <SvgIcon icon={<Gear />} />
                  Settings
                </Dropdown.Item>

                <Dropdown.Item onSelect={signOut}>
                  <SvgIcon icon={<X />} />
                  Sign Out
                </Dropdown.Item>
              </Dropdown.Section>
            </Dropdown.Content>
          </Dropdown.Root>
        ) : (
          <Button
            size="small"
            label="Sign In"
            onClick={signInWithNear}
            type="button"
          />
        )}
      </Flex>
    </header>
  );
};
