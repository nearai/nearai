'use client';

import { Flex, Section, SvgIcon, Text } from '@near-pagoda/ui';
import { CalendarDots } from '@phosphor-icons/react';
import React from 'react';

import { EvaluationsTable } from '~/components/EvaluationsTable';

const CompetitionPage = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => {
  return (
    <>
      <Section background="sand-0">
        <Text as="h1" size="text-2xl" weight="600" className="mb-12">
          {title}
        </Text>

        <Flex align="center" gap="s">
          <SvgIcon icon={<CalendarDots />} color="sand-10" size="l" />
          <Flex direction="column">
            <Text size="text-xs" weight={600}>
              Schedule
            </Text>
            <Text color="sand-12">
              Dec 10th - Jan 15th, 2025 @ 11:59 PM UTC
            </Text>
          </Flex>
        </Flex>
      </Section>

      <Section>{children}</Section>

      <Section>
        <EvaluationsTable
          title="Entries"
          showSidebar={false}
          onlyShowEvaluationsWithMatchingBenchmark
        />
      </Section>
    </>
  );
};

export default CompetitionPage;
