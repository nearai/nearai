'use client';

import {
  Badge,
  Button,
  Card,
  Flex,
  Grid,
  Pattern,
  Section,
  SvgIcon,
  Text,
} from '@near-pagoda/ui';
import {
  ArrowRight,
  CodeBlock,
  DownloadSimple,
  GitFork,
  GithubLogo,
  MagnifyingGlass,
  UserCircle,
} from '@phosphor-icons/react';

import { signInWithNear } from '~/lib/auth';

import s from './page.module.scss';

export default function HomePage() {
  return (
    <Section
      background="sand-0"
      padding="hero"
      style={{ position: 'relative' }}
    >
      <Flex direction="column" gap="xl" align="center">
        <div className={s.dragonLogo} />

        <Flex direction="column" gap="m" align="center" className={s.heroTitle}>
          <Text size="text-2xl" weight="600">
            Build & deploy powerful, user-owned AI agents
          </Text>

          <Text size="text-xl" weight="400" color="sand-11">
            Fork and deploy your first AI agent:
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
              <Text size="text-l" weight="500" color="violet-10">
                1. Sign In
              </Text>
              <SvgIcon
                icon={<UserCircle weight="duotone" />}
                color="violet-10"
                size="m"
              />
            </Flex>

            <Text color="sand-12">
              Quickly sign in to enable forking, deploying, and other hub
              features.
            </Text>

            <Flex direction="column" gap="s" style={{ marginTop: 'auto' }}>
              <Button
                fill="outline"
                variant="secondary"
                label="Sign In"
                onClick={signInWithNear}
                iconRight={<ArrowRight />}
              />
            </Flex>
          </Card>

          <Card background="sand-0" padding="l" gap="l">
            <Flex align="center" justify="space-between" gap="m">
              <Text size="text-l" weight="500" color="cyan-10">
                2. Fork & Deploy
              </Text>
              <SvgIcon
                icon={<GitFork weight="duotone" />}
                color="cyan-10"
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
                href="/agents/flatirons.near/example-travel-agent"
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
              <Text size="text-l" weight="500" color="green-10">
                3. Develop
              </Text>
              <SvgIcon
                icon={<CodeBlock weight="duotone" />}
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
  );
}
