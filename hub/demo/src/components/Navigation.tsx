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
  User,
  X,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

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
    icon: <ChatCircleDots />,
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
    label: 'Inference',
    path: '/inference',
    icon: <Lightbulb />,
  },
  {
    label: 'Benchmarks',
    path: '/benchmarks',
    icon: <ChartBar />,
  },
];

export const Navigation = () => {
  const store = useAuthStore();
  const path = usePathname();

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
        <Tooltip asChild content="View Documentation">
          <Button
            label="View Documentation"
            size="small"
            icon={<BookOpenText weight="duotone" />}
            fill="outline"
            href="https://docs.near.ai"
            target="_blank"
          />
        </Tooltip>

        <BreakpointDisplay show="smaller-than-desktop" className={s.breakpoint}>
          <Dropdown.Root>
            <Dropdown.Trigger asChild>
              <Button
                label="Navigation"
                size="small"
                fill="outline"
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

        {store.isAuthenticated() ? (
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
                    color="sand12"
                    clampLines={1}
                  >
                    {store.auth?.account_id}
                  </Text>
                </Dropdown.SectionContent>
              </Dropdown.Section>

              <Dropdown.Section>
                <Dropdown.Item href="/settings">
                  <SvgIcon icon={<Gear weight="duotone" />} />
                  Settings
                </Dropdown.Item>

                <Dropdown.Item onSelect={() => store.clearAuth()}>
                  <SvgIcon icon={<X weight="regular" />} />
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
