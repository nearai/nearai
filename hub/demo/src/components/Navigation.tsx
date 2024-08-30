'use client';

import {
  BookOpenText,
  ChartBar,
  ChatCircleDots,
  Database,
  Gear,
  Graph,
  Lightbulb,
  List,
  Moon,
  Sun,
  User,
  X,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { signInWithNear } from '~/lib/auth';
import { useAuthStore } from '~/stores/auth';

import { BreakpointDisplay } from './lib/BreakpointDisplay';
import { Button } from './lib/Button';
import { Dropdown } from './lib/Dropdown';
import { Flex } from './lib/Flex';
import { SvgIcon } from './lib/SvgIcon';
import { Text } from './lib/Text';
import { Tooltip } from './lib/Tooltip';
import s from './Navigation.module.scss';

const navItems = [
  {
    label: 'Agents',
    path: '/agents',
    icon: <Lightbulb />,
  },
  {
    label: 'Models',
    path: '/models',
    icon: <Graph />,
  },
  {
    label: 'Datasets',
    path: '/datasets',
    icon: <Database />,
  },
  {
    label: 'Benchmarks',
    path: '/benchmarks',
    icon: <ChartBar />,
  },
  {
    label: 'Chat',
    path: '/chat',
    icon: <ChatCircleDots />,
  },
];

export const Navigation = () => {
  const store = useAuthStore();
  const path = usePathname();
  const [mounted, setMounted] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <header className={s.navigation}>
      <Link className={s.logo} href="/">
        AI Hub
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

        {store.isAuthenticated ? (
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
                    {store.auth?.account_id}
                  </Text>
                </Dropdown.SectionContent>
              </Dropdown.Section>

              <Dropdown.Section>
                <Dropdown.Item href="/settings">
                  <SvgIcon icon={<Gear />} />
                  Settings
                </Dropdown.Item>

                <Dropdown.Item onSelect={() => store.clearAuth()}>
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
