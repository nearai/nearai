'use client';

import { Badge, Button, Card, Flex, Section, SvgIcon, Text } from '@nearai/ui';
import { ArrowRight, CalendarDots } from '@phosphor-icons/react';
import React from 'react';

const ModelTimeline = () => {
  const timelineData = [
    {
      size: '0.5B',
      segments: 23,
      status: 'active',
      offset: 0,
    },
    {
      size: '2B',
      segments: 17,
      status: 'upcoming',
      offset: 40, // Starting with a small offset
    },
    {
      size: '7B',
      segments: 13,
      status: 'planned',
      offset: 80,
    },
    {
      size: '30B',
      segments: 9,
      status: 'planned',
      offset: 120,
    },
    {
      size: '70B',
      segments: 7,
      status: 'planned',
      offset: 160,
    },
    {
      size: '350B',
      segments: 4,
      status: 'planned',
      offset: 200,
    },
    {
      size: '1.4T',
      segments: 2,
      status: 'planned',
      offset: 240,
    },
  ];

  return (
    <Flex direction="column" gap="l">
      <Text size="text-xl">Training Cadence</Text>

      <div style={{ overflowX: 'auto' }}>
        <div style={{ minWidth: '600px' }}>
          {timelineData.map((model) => (
            <Flex
              key={model.size}
              align="center"
              gap="m"
              style={{
                minHeight: '24px',
                opacity: model.status === 'planned' ? 0.7 : 1,
              }}
            >
              <div style={{ width: '60px' }}>
                <Text size="text-xs" weight="500">
                  {model.size}
                </Text>
              </div>

              <div style={{ flex: 1, position: 'relative' }}>
                <Flex
                  gap="s"
                  style={{
                    position: 'absolute',
                    left: model.offset,
                    right: 0,
                  }}
                >
                  {Array.from({ length: model.segments }).map((_, i) => (
                    <div
                      key={i}
                      style={{
                        flex: 1,
                        height: '6px',
                        background:
                          model.status === 'active' && i === 0
                            ? 'var(--violet-7)'
                            : 'var(--sand-8)',
                        borderRadius: '1px',
                      }}
                    />
                  ))}
                </Flex>
              </div>
            </Flex>
          ))}
        </div>
      </div>
    </Flex>
  );
};

// Main component with both the model cards and timeline
const ModelTrainingSeries = () => {
  const models = [
    {
      size: '0.5B',
      status: 'active',
    },
    {
      size: '2B',
      status: 'upcoming',
      startDate: 'Q1 2025',
    },
    {
      size: '7B',
      status: 'planned',
    },
    {
      size: '30B',
      status: 'planned',
    },
    {
      size: '70B',
      status: 'planned',
    },
    {
      size: '350B',
      status: 'planned',
    },
    {
      size: '1.4T',
      status: 'planned',
    },
  ];

  const activeSeries = (
    <Card padding="l" className="mb-12">
      <Flex direction="column" gap="m">
        <Flex gap="m" phone={{ direction: 'column' }}>
          <Flex align="center" gap="s" style={{ marginRight: 'auto' }}>
            <Text
              href="/competitions/0.5b-november-2024"
              size="text-l"
              decoration="none"
            >
              0.5B Parameter Model
            </Text>
            <Badge variant="success" label="Active" size="small" />
          </Flex>
          <Button
            label="View Leaderboard"
            variant="primary"
            href="/competitions/0.5b-november-2024"
            size="small"
            iconRight={<ArrowRight weight="bold" />}
          />
        </Flex>

        <Flex align="center" gap="s">
          <SvgIcon
            icon={<CalendarDots weight="duotone" />}
            color="sand-10"
            size="l"
          />
          <Flex direction="column">
            <Text size="text-s" weight={600}>
              Schedule
            </Text>
            <Text color="sand-11" size="text-s">
              Dec 10th - Jan 15th, 2025 @ 11:59 PM UTC
            </Text>
          </Flex>
        </Flex>
      </Flex>
    </Card>
  );

  return (
    <Section background="sand-2" padding="hero" gap="xl">
      <Flex direction="column" gap="l">
        <Flex direction="column" gap="m">
          <Text as="h2" size="text-2xl">
            Model Training Series
          </Text>
          <Text color="sand-11" size="text-l" weight={400}>
            A progression of increasingly capable models, with parallel
            competitions
          </Text>
        </Flex>

        {activeSeries}
      </Flex>

      <Flex direction="column" gap="l">
        <Text size="text-xl">Model Size Progression</Text>

        <div style={{ overflowX: 'auto', paddingBottom: '1rem' }}>
          <div style={{ minWidth: '800px' }}>
            <Flex gap="m" align="stretch">
              {models.map((model, index) => (
                <Card
                  key={index}
                  href={
                    model.status === 'active'
                      ? '/competitions/0.5b-november-2024'
                      : undefined
                  }
                  padding="m"
                  background={model.status === 'active' ? 'sand-0' : undefined}
                  border={model.status === 'active' ? 'sand-12' : undefined}
                  style={{
                    flex: 1,
                    aspectRatio: 1,
                    opacity: model.status === 'planned' ? 0.7 : 1,
                    position: 'relative',
                    alignItems: 'center',
                    justifyContent: 'center',
                    textAlign: 'center',
                  }}
                >
                  {/* Connector line */}
                  {index < models.length - 1 && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '50%',
                        right: 'calc(-1rem - 1px)',
                        width: '1rem',
                        height: '2px',
                        background: 'var(--sand-6)',
                        zIndex: 0,
                      }}
                    />
                  )}

                  <Text
                    size="text-xl"
                    indicateParentClickable
                    color={model.status === 'planned' ? 'sand-11' : undefined}
                  >
                    {model.size}
                  </Text>

                  {model.status === 'active' && (
                    <Badge variant="success" label="Active" />
                  )}
                  {model.status === 'upcoming' && (
                    <Badge variant="neutral" label={model.startDate} />
                  )}
                  {model.status === 'planned' && (
                    <Badge variant="neutral-alpha" label="Planned" />
                  )}
                </Card>
              ))}
            </Flex>
          </div>
        </div>
      </Flex>

      <ModelTimeline />
    </Section>
  );
};

export default ModelTrainingSeries;
