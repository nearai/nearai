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
  CaretDown,
  ChatCircleDots,
  Cube,
  Gear,
  GithubLogo,
  List,
  Moon,
  Plus,
  Star,
  Sun,
  User,
  X,
} from '@phosphor-icons/react';
import * as NavigationMenu from '@radix-ui/react-navigation-menu';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { APP_TITLE } from '~/constants';
import { env } from '~/env';
import { signInWithNear } from '~/lib/auth';
import { ENTRY_CATEGORY_LABELS } from '~/lib/entries';
import { useAuthStore } from '~/stores/auth';
import { useWalletStore } from '~/stores/wallet';
import { trpc } from '~/trpc/TRPCProvider';

import s from './Navigation.module.scss';
import { NewAgentButton } from './NewAgentButton';

const agentsNav = {
  label: 'Agents',
  path: '/agents',
  icon: ENTRY_CATEGORY_LABELS.agent.icon,
};

const hubNavItems = [
  agentsNav,
  {
    label: 'Threads',
    path: '/chat',
    icon: <ChatCircleDots />,
  },
];

const chatNavItems = [
  {
    label: 'Chat',
    path: '/chat',
    icon: <ChatCircleDots />,
  },
  agentsNav,
];

const navItems = env.NEXT_PUBLIC_CONSUMER_MODE ? chatNavItems : hubNavItems;

const resourcesNavItems = env.NEXT_PUBLIC_CONSUMER_MODE
  ? null
  : [
      {
        label: 'Datasets',
        path: '/datasets',
        icon: ENTRY_CATEGORY_LABELS.dataset.icon,
      },
      {
        label: 'Evaluations',
        path: '/evaluations',
        icon: ENTRY_CATEGORY_LABELS.evaluation.icon,
      },
      {
        label: 'Models',
        path: '/models',
        icon: ENTRY_CATEGORY_LABELS.model.icon,
      },
      {
        label: 'Documentation',
        path: 'https://docs.near.ai',
        target: '_blank',
        icon: <BookOpenText />,
      },
      {
        label: 'NEAR AI CLI',
        path: 'https://github.com/nearai/nearai',
        target: '_blank',
        icon: <GithubLogo />,
      },
    ];

export const Navigation = () => {
  const auth = useAuthStore((store) => store.auth);
  const clearAuth = useAuthStore((store) => store.clearAuth);
  const clearTokenMutation = trpc.auth.clearToken.useMutation();
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const wallet = useWalletStore((store) => store.wallet);
  const path = usePathname();
  const [mounted, setMounted] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  const signOut = () => {
    if (wallet) {
      void wallet.signOut();
    }
    void clearTokenMutation.mutate();
    clearAuth();
  };

  return (
    <header className={s.navigation}>
      <Link className={s.logo} href="/">
        <span className={s.logoNearAi}>NEAR AI</span>
        <span className={s.logoTitle}>{APP_TITLE}</span>
      </Link>

      <BreakpointDisplay show="larger-than-tablet" className={s.breakpoint}>
        <NavigationMenu.Root className={s.menu} delayDuration={0}>
          <NavigationMenu.List>
            {navItems.map((item) => (
              <NavigationMenu.Item key={item.path}>
                <NavigationMenu.Link
                  asChild
                  active={path.startsWith(item.path)}
                >
                  <Link href={item.path} key={item.path}>
                    {item.label}
                  </Link>
                </NavigationMenu.Link>
              </NavigationMenu.Item>
            ))}

            {resourcesNavItems ? (
              <NavigationMenu.Item>
                <NavigationMenu.Trigger>
                  Resources
                  <SvgIcon size="xs" icon={<CaretDown />} />
                </NavigationMenu.Trigger>

                <NavigationMenu.Content className={s.menuDropdown}>
                  {resourcesNavItems.map((item) => (
                    <NavigationMenu.Link
                      key={item.path}
                      asChild
                      active={path.startsWith(item.path)}
                    >
                      <Link
                        href={item.path}
                        target={item.target}
                        key={item.path}
                      >
                        <SvgIcon icon={item.icon} />
                        {item.label}
                      </Link>
                    </NavigationMenu.Link>
                  ))}
                </NavigationMenu.Content>
              </NavigationMenu.Item>
            ) : null}
          </NavigationMenu.List>
        </NavigationMenu.Root>
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

          <NewAgentButton
            customButton={
              <Button
                label="New Agent"
                size="small"
                icon={<Plus weight="bold" />}
                variant="affirmative"
                fill="ghost"
              />
            }
          />
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

              {/* The following code is left commented out in case we add a nav dropdown again in the near future: */}

              {/* {resourcesNav ? (
                <Dropdown.Section>
                  {resourcesNav.map((item) => (
                    <Dropdown.Item href={item.path} key={item.path}>
                      <SvgIcon icon={item.icon} />
                      {item.label}
                    </Dropdown.Item>
                  ))}
                </Dropdown.Section>
              ) : null} */}
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
