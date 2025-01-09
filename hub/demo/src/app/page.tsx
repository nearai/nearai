'use client';

import {
  Badge,
  Button,
  Card,
  Flex,
  Grid,
  HR,
  IconCircle,
  Section,
  SvgIcon,
  Text,
} from '@near-pagoda/ui';
import {
  ArrowRight,
  ArrowSquareUpRight,
  Book,
  ChartBar,
  ChatCircle,
  Check,
  CloudCheck,
  CodeBlock,
  Database,
  DownloadSimple,
  GitFork,
  GithubLogo,
  HandCoins,
  Handshake,
  LockKey,
  MagnifyingGlass,
  UserCircle,
} from '@phosphor-icons/react';

import { env } from '~/env';
import { signInWithNear } from '~/lib/auth';
import { useAuthStore } from '~/stores/auth';

import s from './page.module.scss';

export default function HomePage() {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);

  return (
    <>
      <Section background="sand-0" padding="hero" className={s.heroSection}>
        <Flex direction="column" gap="xl" align="center">
          <div className={s.dragonLogo} />

          <Flex
            direction="column"
            gap="l"
            align="center"
            className={s.heroTitle}
          >
            <Text size="text-2xl" weight="600">
              Build powerful, user-owned AI agents
            </Text>

            <Text size="text-xl" weight="400" color="sand-10">
              Fork, develop, and deploy with{' '}
              <Text as="span" size="text-xl" weight="400" color="sand-12">
                free inference and hosting:
              </Text>
            </Text>
          </Flex>

          <Grid
            columns="1fr 1fr 1fr"
            tablet={{ columns: '1fr 1fr' }}
            gap="m"
            className={s.heroCards}
          >
            <Card background="sand-0" padding="l" gap="l">
              <Flex align="center" justify="space-between" gap="m">
                <Text size="text-l" weight="500" color="sand-11">
                  1. Sign In
                </Text>
                <SvgIcon
                  icon={<UserCircle weight="regular" />}
                  color="violet-9"
                  size="m"
                />
              </Flex>

              <Text color="sand-12">
                Quickly sign in to enable forking, deploying, and other hub
                features.
              </Text>

              <Flex direction="column" gap="s" style={{ marginTop: 'auto' }}>
                {isAuthenticated ? (
                  <Flex align="center" gap="s">
                    <SvgIcon icon={<Check />} color="sand-10" />
                    <Text color="sand-10">{`You're`} signed in.</Text>
                  </Flex>
                ) : (
                  <Button
                    fill="outline"
                    variant="secondary"
                    label="Sign In"
                    onClick={signInWithNear}
                    iconRight={<ArrowRight />}
                  />
                )}
              </Flex>
            </Card>

            <Card background="sand-0" padding="l" gap="l">
              <Flex align="center" justify="space-between" gap="m">
                <Text size="text-l" weight="500" color="sand-11">
                  2. Fork & Deploy
                </Text>
                <SvgIcon
                  icon={<GitFork weight="regular" />}
                  color="cyan-9"
                  size="m"
                />
              </Flex>

              <Text color="sand-12">
                Forking an agent will deploy a copy under your namespace -
                available for the world to interact with.
              </Text>

              <Text size="text-s">
                Not sure where to start? View this{' '}
                <Text
                  size="text-s"
                  href={`/agents/${env.NEXT_PUBLIC_EXAMPLE_FORK_AGENT_ID}`}
                >
                  Example Agent
                </Text>{' '}
                and click the{' '}
                <Badge
                  iconLeft={<GitFork />}
                  label="Fork"
                  variant="primary"
                  size="small"
                />{' '}
                button.
              </Text>

              <Flex direction="column" gap="s" style={{ marginTop: 'auto' }}>
                <Button
                  variant="secondary"
                  fill="outline"
                  label="Browse Agents"
                  href="/agents"
                  iconLeft={<MagnifyingGlass />}
                />
              </Flex>
            </Card>

            <Card background="sand-0" padding="l" gap="l">
              <Flex align="center" justify="space-between" gap="m">
                <Text size="text-l" weight="500" color="sand-11">
                  3. Develop
                </Text>
                <SvgIcon
                  icon={<CodeBlock weight="regular" />}
                  color="green-10"
                  size="m"
                />
              </Flex>

              <Text color="sand-12">
                Use the{' '}
                <Text href="https://github.com/nearai/nearai" target="_blank">
                  Near AI CLI
                </Text>{' '}
                to develop and deploy changes to your agent.
              </Text>

              <Text size="text-s">
                Click the{' '}
                <Badge
                  iconLeft={<DownloadSimple />}
                  label="Develop"
                  variant="success"
                  size="small"
                />{' '}
                button when viewing an agent to copy and paste CLI commands for
                getting started.
              </Text>

              <Flex direction="column" gap="s" style={{ marginTop: 'auto' }}>
                <Button
                  variant="secondary"
                  fill="outline"
                  label="Near AI CLI"
                  href="https://github.com/nearai/nearai"
                  target="_blank"
                  iconLeft={<GithubLogo />}
                />
              </Flex>
            </Card>
          </Grid>
        </Flex>
      </Section>

      <Section padding="hero" background="sand-1">
        <Flex direction="column" gap="m">
          <Text
            as="h2"
            size="text-2xl"
            weight="600"
            style={{ textAlign: 'center' }}
          >
            AI Agent Protocol
          </Text>

          <Text
            size="text-l"
            weight="400"
            style={{ textAlign: 'center' }}
            color="sand-10"
          >
            The open standard for AI agents to connect, act, and transact
          </Text>
        </Flex>

        <HR />

        <Grid
          columns="1fr 1fr 1fr 1fr"
          tablet={{ columns: '1fr 1fr' }}
          phone={{ columns: '1fr' }}
          gap="l"
          style={{ textAlign: 'center' }}
        >
          <Flex direction="column" gap="m" align="center">
            <IconCircle
              icon={<CloudCheck weight="duotone" />}
              color="violet-9"
            />
            <Text weight={500} color="sand-12">
              Free inference and hosting
            </Text>
          </Flex>

          <Flex direction="column" gap="m" align="center">
            <IconCircle icon={<Handshake weight="duotone" />} color="cyan-10" />
            <Text weight={500} color="sand-12">
              Connect across Web2 and Web3 services
            </Text>
          </Flex>

          <Flex direction="column" gap="m" align="center">
            <IconCircle icon={<LockKey weight="duotone" />} color="amber-11" />
            <Text weight={500} color="sand-12">
              Protect your data and identity
            </Text>
          </Flex>

          <Flex direction="column" gap="m" align="center">
            <IconCircle
              icon={<HandCoins weight="duotone" />}
              color="green-10"
            />
            <Text weight={500} color="sand-12">
              Authorize and complete payments seamlessly
            </Text>
            <Badge label="Coming Soon" variant="neutral-alpha" />
          </Flex>
        </Grid>

        {/* Connect across Web2 and Web3 services Authorize and complete payments
        seamlessly Protect your data and identity */}
      </Section>

      <Section padding="hero" background="sand-3">
        <Flex direction="column" gap="l">
          <Flex direction="column" gap="m">
            <Text as="h2" size="text-2xl" weight="600">
              Resources
            </Text>
            <Text color="sand-11" size="text-l" weight={400}>
              Everything you need to get started
            </Text>
          </Flex>

          <Grid
            columns="1fr 1fr 1fr 1fr"
            gap="m"
            tablet={{ columns: '1fr 1fr' }}
            phone={{ columns: '1fr' }}
          >
            {[
              {
                icon: <Book weight="duotone" />,
                title: 'Documentation',
                description: 'Get started with our infrastructure',
                link: 'Learn More',
                href: 'https://docs.near.ai/',
              },
              {
                icon: <ChartBar weight="duotone" />,
                title: 'Benchmarks',
                description: 'Understand our evaluation metrics',
                link: 'Explore',
                href: '/benchmarks',
              },
              {
                icon: <Database weight="duotone" />,
                title: 'Datasets',
                description: 'Contribute to training and evaluation data',
                link: 'Browse',
                href: '/datasets',
              },
              {
                icon: <ChatCircle weight="duotone" />,
                title: 'Community',
                description: 'Connect with other researchers',
                link: 'Join',
                href: 'https://t.me/nearaialpha',
                target: '_blank',
              },
            ].map((resource, index) => (
              <Card key={index} padding="l">
                <SvgIcon icon={resource.icon} size="l" color="violet-9" />
                <Text size="text-l" weight="600">
                  {resource.title}
                </Text>
                <Text color="sand-11">{resource.description}</Text>
                <Button
                  label={resource.link}
                  variant="secondary"
                  fill="outline"
                  iconRight={
                    resource.target == '_blank' ? (
                      <ArrowSquareUpRight weight="bold" />
                    ) : (
                      <ArrowRight weight="bold" />
                    )
                  }
                  href={resource.href}
                  style={{ marginTop: 'auto' }}
                  target={resource.target}
                />
              </Card>
            ))}
          </Grid>
        </Flex>
      </Section>
    </>
  );
}
