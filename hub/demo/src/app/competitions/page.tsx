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
} from '@nearai/ui';
import {
  ArrowSquareOut,
  Book,
  ChartBar,
  ChatCircle,
  CirclesFour,
  Cloud,
  Code,
  Database,
  Lightbulb,
  Robot,
} from '@phosphor-icons/react';
import React from 'react';

import ModelTrainingSeries from '@/app/competitions/ModelTrainingSeries';

const CompetitionsPage = () => {
  const visionStuff = (
    <Section background="sand-0">
      <Pattern patternMaskedBackground="linear-gradient(to bottom right, var(--violet-brand), var(--green-brand))">
        <Grid
          columns="1fr 1px 1fr"
          gap="l"
          phone={{ columns: '1fr' }}
          style={{ paddingBlock: '0.5rem' }}
        >
          <Flex direction="column" gap="l">
            <Flex direction="column" gap="m">
              <Text size="text-2xl" weight="600">
                Build agents & models
              </Text>
              <Text size="text-l" color="sand-11" weight={450}>
                NEAR AI Agents are the building block for the user-owned AI
                ecosystem
              </Text>
            </Flex>
            {[
              {
                icon: <Robot weight="duotone" />,
                text: 'Train and evaluate models through our benchmarks and competitions',
              },
              {
                icon: <CirclesFour weight="duotone" />,
                text: 'Interact with models, users, and other AI agents across Web2 and Web3',
              },
              {
                icon: <Cloud weight="duotone" />,
                content: (
                  <Flex align="center" gap="s">
                    <Text as="span" size="text-s">
                      Connect and transact with external services and APIs
                    </Text>
                    <Badge label="Coming Soon" variant="neutral-alpha" />
                  </Flex>
                ),
              },
            ].map((item, index) => (
              <Flex align="center" gap="m" key={index}>
                <SvgIcon icon={item.icon} size="m" color="violet-9" />
                {item.content ?? (
                  <Text as="span" size="text-s">
                    {item.text}
                  </Text>
                )}
              </Flex>
            ))}
          </Flex>

          <div
            style={{
              borderLeft: '1px solid var(--sand-4)',
              borderTop: '1px solid var(--sand-4)',
            }}
          />

          <Flex direction="column" gap="l">
            <Flex direction="column" gap="m">
              <Text size="text-2xl" weight="600">
                A new model for AI development
              </Text>
              <Text size="text-l" color="sand-11" weight={450}>
                Contribute to an open ecosystem with fair rewards
              </Text>
            </Flex>
            {[
              {
                icon: <Code weight="duotone" />,
                content: (
                  <Text as="span" size="text-s">
                    Enter your solutions in targeted challenges or join the
                    ongoing Model Training Series
                  </Text>
                ),
              },
              {
                icon: <Lightbulb weight="duotone" />,
                content: (
                  <Flex align="center" gap="s">
                    <Text as="span" size="text-s">
                      Earn rewards and royalties from competitions and model
                      usage
                    </Text>
                    <Badge label="Coming Soon" variant="neutral-alpha" />
                  </Flex>
                ),
              },
            ].map((item, index) => (
              <Flex align="center" gap="m" key={index}>
                <SvgIcon icon={item.icon} size="m" color="violet-9" />
                {item.content}
              </Flex>
            ))}
          </Flex>
        </Grid>
      </Pattern>
    </Section>
  );

  // const otherCompetitions = (
  //   <Section padding="hero" gap="l">
  //     {/* Other Competitions */}
  //     <Flex direction="column" gap="m">
  //       <Text as="h2" size="text-2xl" weight="600">
  //         Other Active Competitions
  //       </Text>
  //     </Flex>

  //     <Card padding="l">
  //       <Grid columns="1fr auto" gap="xl" phone={{ columns: '1fr' }}>
  //         <Flex direction="column" gap="m">
  //           <Text size="text-xl" weight="600" decoration="none">
  //             Lean Benchmark Challenge
  //           </Text>
  //           <Text color="sand-11">
  //             Deadline: <b>Nov 30 @ 11:59 PM UTC</b>
  //           </Text>
  //         </Flex>

  //         <Button label="Begins November 11" variant="primary" disabled />
  //       </Grid>
  //     </Card>
  //   </Section>
  // );

  const resources = (
    <Section padding="hero">
      <Flex direction="column" gap="l">
        <Flex direction="column" gap="m">
          <Text as="h2" size="text-2xl" weight="600">
            Resources
          </Text>
          <Text color="sand-11" size="text-l" weight={400}>
            Everything you need to get started
          </Text>
        </Flex>

        <Grid columns="1fr 1fr 1fr 1fr" gap="l" phone={{ columns: '1fr' }}>
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
            },
          ].map((resource, index) => (
            <Card key={index} padding="l">
              <Flex direction="column" gap="m">
                <SvgIcon icon={resource.icon} size="l" color="violet-9" />
                <Text size="text-l" weight="600">
                  {resource.title}
                </Text>
                <Text color="sand-11">{resource.description}</Text>
                <Button
                  label={resource.link}
                  variant="secondary"
                  fill="outline"
                  iconRight={<ArrowSquareOut weight="bold" />}
                  href={resource.href}
                />
              </Flex>
            </Card>
          ))}
        </Grid>
      </Flex>
    </Section>
  );

  return (
    <>
      {visionStuff}
      <ModelTrainingSeries />
      {/* {otherCompetitions} */}
      {resources}
    </>
  );
};

export default CompetitionsPage;
