'use client';

import { ImageIcon, useTheme } from '@nearai/ui';
import {
  BreakpointDisplay,
  Button,
  Dropdown,
  Flex,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
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
  SignOut,
  Star,
  Sun,
  User,
  Wallet,
  X,
} from '@phosphor-icons/react';
import * as NavigationMenu from '@radix-ui/react-navigation-menu';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { APP_TITLE } from '@/constants';
import { env } from '@/env';
import { useEmbeddedWithinIframe } from '@/hooks/embed';
import { useCurrentEntry } from '@/hooks/entries';
import { SIGN_IN_CALLBACK_PATH, signIn } from '@/lib/auth';
import { ENTRY_CATEGORY_LABELS } from '@/lib/categories';
import { rawFileUrlForEntry } from '@/lib/entries';
import { useAuthStore } from '@/stores/auth';
import { useWalletStore } from '@/stores/wallet';
import NearAiLogo from '@/svgs/near-ai-logo.svg';
import { trpc } from '@/trpc/TRPCProvider';

import s from './Navigation.module.scss';
import { NewAgentButton } from './NewAgentButton';

const hubNavItems = [
  {
    label: 'Agents',
    path: '/agents',
    icon: ENTRY_CATEGORY_LABELS.agent.icon,
  },
  {
    label: 'Threads',
    path: '/chat',
    icon: <ChatCircleDots />,
  },
];

const navItems = env.NEXT_PUBLIC_CONSUMER_MODE ? null : hubNavItems;

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

export function computeNavigationHeight() {
  try {
    const bodyStyle = getComputedStyle(document.body, null);
    const height = parseInt(
      bodyStyle.getPropertyValue('--header-height').replace('px', ''),
    );
    return height;
  } catch (error) {
    console.error(
      'Failed to compute navigation height in returnNavigationHeight()',
      error,
    );
  }

  return 0;
}

export const Navigation = () => {
  const auth = useAuthStore((store) => store.auth);
  const clearAuth = useAuthStore((store) => store.clearAuth);
  const clearTokenMutation = trpc.auth.clearToken.useMutation();
  const wallet = useWalletStore((store) => store.wallet);
  const walletModal = useWalletStore((store) => store.modal);
  const walletAccount = useWalletStore((store) => store.account);
  const path = usePathname();
  const [mounted, setMounted] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();
  const { embedded } = useEmbeddedWithinIframe();
  const hidden = path === SIGN_IN_CALLBACK_PATH;
  const { currentEntry, currentEntryId } = useCurrentEntry('agent', {
    enabled: embedded,
  });

  useEffect(() => {
    if (hidden) {
      document.body.style.setProperty('--header-height', '0px');
      document.body.style.setProperty('--section-fill-height', '100svh');
    }
  }, [hidden]);

  useEffect(() => {
    setMounted(true);
  }, []);

  const signOut = () => {
    void clearTokenMutation.mutate();
    clearAuth();
    if (wallet) {
      void wallet.signOut();
    }
  };

  const disconnectWallet = () => {
    if (wallet) {
      void wallet.signOut();
    }
  };

  if (hidden) return null;

  return (
    <header className={s.navigation}>
      {embedded ? (
        <>
          {currentEntry &&
            currentEntry.details.agent?.embed?.logo !== false && (
              <div className={s.embeddedLogo}>
                {currentEntry.details.agent?.embed?.logo ? (
                  <img
                    src={rawFileUrlForEntry(
                      currentEntry,
                      currentEntry.details.agent.embed.logo,
                    )}
                    alt={currentEntry.name}
                  />
                ) : (
                  <span className={s.logoTitle}>{currentEntry.name}</span>
                )}
              </div>
            )}
        </>
      ) : (
        <Link className={s.logo} href="/">
          <NearAiLogo className={s.logoNearAi} />
          <span className={s.logoTitle}>{APP_TITLE}</span>
        </Link>
      )}

      {!embedded && (
        <BreakpointDisplay show="larger-than-tablet" className={s.breakpoint}>
          <NavigationMenu.Root className={s.menu} delayDuration={0}>
            <NavigationMenu.List>
              {navItems?.map((item) => (
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

              {resourcesNavItems && (
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
              )}
            </NavigationMenu.List>
          </NavigationMenu.Root>
        </BreakpointDisplay>
      )}

      <Flex
        align="center"
        gap="m"
        phone={{ gap: 's' }}
        style={{ marginLeft: 'auto' }}
      >
        {embedded ? (
          <a
            href={`https://app.near.ai/agents/${currentEntryId}`}
            target="_blank"
            className={s.poweredByNearAiLogo}
          >
            <Text size="text-2xs">Powered by</Text>
            <NearAiLogo />
          </a>
        ) : (
          <>
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

              {!env.NEXT_PUBLIC_CONSUMER_MODE && (
                <>
                  <BreakpointDisplay
                    show="larger-than-phone"
                    className={s.breakpoint}
                  >
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
                  </BreakpointDisplay>

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
                </>
              )}
            </Flex>

            {(navItems || resourcesNavItems) && (
              <BreakpointDisplay
                show="smaller-than-desktop"
                className={s.breakpoint}
              >
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

                  <Dropdown.Content maxHeight="80svh">
                    <Dropdown.Section>
                      {navItems?.map((item) => (
                        <Dropdown.Item href={item.path} key={item.path}>
                          <SvgIcon icon={item.icon} />
                          {item.label}
                        </Dropdown.Item>
                      ))}
                    </Dropdown.Section>

                    {resourcesNavItems && (
                      <Dropdown.Section>
                        {resourcesNavItems.map((item) => (
                          <Dropdown.Item href={item.path} key={item.path}>
                            <SvgIcon icon={item.icon} />
                            {item.label}
                          </Dropdown.Item>
                        ))}
                      </Dropdown.Section>
                    )}
                  </Dropdown.Content>
                </Dropdown.Root>
              </BreakpointDisplay>
            )}
          </>
        )}

        {auth ? (
          <Dropdown.Root>
            <Dropdown.Trigger asChild>
              <Button
                label="User Settings"
                size="small"
                icon={<User weight="bold" />}
              />
            </Dropdown.Trigger>

            <Dropdown.Content style={{ width: '14rem' }} maxHeight="80svh">
              <Dropdown.Section>
                <Dropdown.SectionContent>
                  <Flex direction="column" gap="m">
                    <Text size="text-xs" weight={600} uppercase>
                      Account
                    </Text>

                    <Text
                      size="text-s"
                      weight={600}
                      color="sand-12"
                      clampLines={1}
                    >
                      {auth.accountId}
                    </Text>
                  </Flex>
                </Dropdown.SectionContent>

                {!env.NEXT_PUBLIC_CONSUMER_MODE && !embedded && (
                  <>
                    <Dropdown.Item href={`/profiles/${auth.accountId}`}>
                      <SvgIcon icon={<Cube />} />
                      Your Work
                    </Dropdown.Item>

                    <Dropdown.Item href={`/profiles/${auth.accountId}/starred`}>
                      <SvgIcon icon={<Star />} />
                      Your Stars
                    </Dropdown.Item>
                  </>
                )}

                {!embedded && (
                  <Dropdown.Item href="/settings">
                    <SvgIcon icon={<Gear />} />
                    Settings
                  </Dropdown.Item>
                )}

                <Dropdown.Item onSelect={signOut}>
                  <SvgIcon icon={<SignOut />} />
                  Sign Out
                </Dropdown.Item>
              </Dropdown.Section>

              {!embedded && (
                <>
                  {/* https://github.com/nearai/nearai/issues/952 */}

                  {wallet && walletAccount ? (
                    <Dropdown.Section>
                      <Dropdown.SectionContent>
                        <Flex direction="column" gap="m">
                          <Text size="text-xs" weight={600} uppercase>
                            Payment Method
                          </Text>

                          <Flex align="center" gap="s">
                            <ImageIcon
                              src={wallet.metadata.iconUrl}
                              alt={wallet.metadata.name}
                            />

                            <Flex direction="column">
                              <Text
                                size="text-s"
                                weight={600}
                                color="sand-12"
                                clampLines={1}
                              >
                                {walletAccount.accountId}
                              </Text>
                              <Text size="text-xs" clampLines={1}>
                                {wallet.metadata.name}
                              </Text>
                            </Flex>
                          </Flex>
                        </Flex>
                      </Dropdown.SectionContent>

                      <Dropdown.Item onSelect={disconnectWallet}>
                        <SvgIcon icon={<X />} />
                        Disconnect
                      </Dropdown.Item>
                    </Dropdown.Section>
                  ) : (
                    <Dropdown.Section>
                      <Dropdown.SectionContent>
                        <Flex direction="column" gap="m">
                          <Text size="text-xs" weight={600} uppercase>
                            Payment Method
                          </Text>

                          <Text size="text-xs">
                            Certain agent interactions require a connected
                            wallet.
                          </Text>
                        </Flex>
                      </Dropdown.SectionContent>

                      <Dropdown.Item onSelect={() => walletModal?.show()}>
                        <SvgIcon icon={<Wallet />} />
                        Add Payment Method
                      </Dropdown.Item>
                    </Dropdown.Section>
                  )}
                </>
              )}
            </Dropdown.Content>
          </Dropdown.Root>
        ) : (
          <Button size="small" label="Sign In" onClick={signIn} />
        )}
      </Flex>
    </header>
  );
};
