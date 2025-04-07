'use client';

import {
  Badge,
  Button,
  Card,
  Flex,
  Grid,
  IconCircle,
  Section,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import {
  ArrowRight,
  ArrowSquareUpRight,
  BookOpenText,
  Brain,
  ChartBar,
  ChatCircle,
  Check,
  CloudCheck,
  Code,
  CodeBlock,
  DownloadSimple,
  GitFork,
  HandCoins,
  Handshake,
  Lightning,
  LockKey,
  MagnifyingGlass,
  Question,
  ShieldCheck,
  TwitterLogo,
  UserCircle,
  XLogo,
} from '@phosphor-icons/react';

import { env } from '@/env';
import { signIn } from '@/lib/auth';
import { useAuthStore } from '@/stores/auth';
import NearLogoIcon from '@/svgs/near-logo-icon-padding.svg';

import s from './page.module.scss';

export default function HomePage() {
  const auth = useAuthStore((store) => store.auth);

  return (
    <>
      <Section background="sand-0" padding="hero">
        <Flex direction="column" gap="xl" align="center">
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

          <div className={s.heroCards}>
            <Card background="sand-0" padding="l" gap="l">
              <Flex align="center" justify="space-between" gap="m">
                <Text size="text-l" weight="500" color="sand-11">
                  1. Sign In
                </Text>
                <SvgIcon
                  icon={<UserCircle weight="regular" />}
                  color="sand-8"
                  size="m"
                />
              </Flex>

              <Text color="sand-12">
                Quickly sign in to enable forking, deploying, and other hub
                features.
              </Text>

              <Flex direction="column" gap="s" style={{ marginTop: 'auto' }}>
                {auth ? (
                  <Flex align="center" gap="s">
                    <SvgIcon icon={<Check />} color="sand-10" />
                    <Text color="sand-10">{`You're`} signed in.</Text>
                  </Flex>
                ) : (
                  <Button
                    label="Sign In"
                    fill="outline"
                    onClick={signIn}
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
                  color="sand-8"
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
                  label="Browse Agents"
                  fill="outline"
                  href="/agents"
                  iconLeft={<MagnifyingGlass />}
                />
              </Flex>
            </Card>

            <Card background="sand-0" padding="l" gap="l">
              <Flex align="center" justify="space-between" gap="m">
                <Text size="text-l" weight="500" color="sand-11">
                  3. Build
                </Text>
                <SvgIcon
                  icon={<CodeBlock weight="regular" />}
                  color="sand-8"
                  size="m"
                />
              </Flex>

              <Text color="sand-12">
                Use the{' '}
                <Text href="https://github.com/nearai/nearai" target="_blank">
                  NEAR AI CLI
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
                  label="View Docs"
                  fill="outline"
                  href="https://docs.near.ai"
                  iconLeft={<BookOpenText />}
                />
              </Flex>
            </Card>
          </div>

          <Flex align="center" gap="s" className={s.heroFooter}>
            <SvgIcon icon={<Lightning weight="fill" />} color="amber-10" />
            <Text weight={500} color="sand-12">
              It only takes 5 minutes to{' '}
              <Text
                href="https://docs.near.ai/agents/quickstart"
                target="_blank"
              >
                deploy your first agent
              </Text>
            </Text>
          </Flex>
        </Flex>
      </Section>

      <Section padding="hero" background="sand-1" gap="xl">
        <Flex direction="column" gap="m">
          <Text as="h2" size="text-2xl" weight="600">
            AI Agent Protocol
          </Text>

          <Text size="text-l" weight="400" color="sand-10">
            The open standard for AI agents to connect, act, and transact
          </Text>
        </Flex>

        <Grid gap="xl" columns="1fr 1fr" tablet={{ columns: '1fr' }}>
          <Flex gap="m" align="center">
            <IconCircle
              icon={<CloudCheck weight="duotone" />}
              color="violet-9"
            />

            <Flex direction="column" gap="xs" align="start">
              <Text weight={500} color="sand-12">
                Free inference and hosting
              </Text>
              <Text size="text-s">
                Deploy, build, and grow your agents with peace of mind
              </Text>
            </Flex>
          </Flex>

          <Flex gap="m" align="center">
            <IconCircle icon={<Handshake weight="duotone" />} color="cyan-9" />

            <Flex direction="column" gap="xs" align="start">
              <Text weight={500} color="sand-12">
                Connect across Web2 and Web3 services
              </Text>
              <Flex align="center" gap="s" wrap="wrap">
                <Tooltip
                  asChild
                  content="View an agent integrated with X (Twitter)"
                >
                  <Button
                    size="small"
                    icon={<XLogo />}
                    label="Twitter / X"
                    iconRight={<TwitterLogo />}
                    href="/agents/flatirons.near/near-secret-agent/latest"
                  />
                </Tooltip>

                <Tooltip asChild content="View an agent integrated with NEAR">
                  <Button
                    size="small"
                    icon={<NearLogoIcon />}
                    label="Near"
                    href="/agents/zavodil.near/near-agent/latest"
                  />
                </Tooltip>

                <Badge label="More Coming Soon" variant="neutral-alpha" />
              </Flex>
            </Flex>
          </Flex>

          <Flex gap="m" align="center">
            <IconCircle
              icon={<HandCoins weight="duotone" />}
              color="green-10"
            />

            <Flex direction="column" gap="xs" align="start">
              <Text weight={500} color="sand-12">
                Authorize and complete payments seamlessly
              </Text>
              <Text size="text-s">Monetize your agents via fiat or crypto</Text>
              <Badge label="Coming Soon" variant="neutral-alpha" />
            </Flex>
          </Flex>

          <Flex gap="m" align="center">
            <IconCircle icon={<LockKey weight="duotone" />} color="amber-10" />

            <Flex direction="column" gap="xs" align="start">
              <Text weight={500} color="sand-12">
                Protect your data
              </Text>
              <Text size="text-s">
                Run agents and inference in a private, trusted execution
                environment
              </Text>
              <Badge label="Coming Soon" variant="neutral-alpha" />
            </Flex>
          </Flex>
        </Grid>
      </Section>

      <Section padding="hero" background="sand-2">
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
                icon: <BookOpenText weight="duotone" />,
                title: 'Documentation',
                description: 'Get started with our infrastructure',
                label: 'Learn More',
                href: 'https://docs.near.ai',
              },
              {
                icon: <ChartBar weight="duotone" />,
                title: 'Evaluations',
                description: 'Understand our evaluation metrics',
                label: 'Explore',
                href: '/evaluations',
              },
              {
                icon: <Question weight="duotone" />,
                title: 'FAQ',
                description: 'Find answers to common developer questions',
                label: 'View FAQ',
                href: 'https://github.com/nearai/nearai/issues/1080',
                target: '_blank',
              },
              {
                icon: <ChatCircle weight="duotone" />,
                title: 'Community',
                description: 'Connect with other developers',
                label: 'Join',
                href: 'https://t.me/nearaialpha',
                target: '_blank',
              },
              // Second row
              {
                icon: <Code weight="duotone" />,
                title: 'TypeScript Agents',
                description:
                  'Learn how to develop TypeScript agents that can utilize a variety of packages, including Coinbase AgentKit',
                label: 'View Code',
                href: 'https://github.com/nearai/nearai/tree/main/ts_runner/ts_agent_runner',
                target: '_blank',
              },
              {
                icon: <Brain weight="duotone" />,
                title: 'LangChain and Coinbase Python Agents',
                description:
                  'Utilize LangChain, LangGraph, and Coinbase AgentKit Python functions on NEAR AI',
                label: 'Explore',
                href: 'https://github.com/nearai/nearai_langchain',
                target: '_blank',
              },
              {
                icon: <ShieldCheck weight="duotone" />,
                title: 'Trusted Execution Environment',
                description:
                  'A secure environment for running LLM workloads with guaranteed privacy and security',
                label: 'Learn More',
                href: 'https://github.com/nearai/private-ml-sdk',
                target: '_blank',
              },
              {
                icon: <Lightning weight="duotone" />,
                title: 'Agent Interaction and Transaction Protocol (AITP)',
                description:
                  'Standard protocol for secure agent-to-agent and user-to-agent communication',
                label: 'Learn More',
                href: 'https://aitp.dev/',
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
                  label={resource.label}
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
