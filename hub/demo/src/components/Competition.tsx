'use client';

import { Flex, Section, SvgIcon, Text } from '@nearai/ui';
import { CalendarDots } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { CompetitionLeaderboardTable } from './CompetitionLeaderboardTable';

type Props = {
  competitionId: string;
  title: string;
  children: ReactNode;
  schedule: string;
};

export const Competition = ({
  competitionId,
  title,
  children,
  schedule,
}: Props) => {
  return (
    <>
      <Section background="sand-0">
        <Text as="h1" size="text-2xl" weight="600">
          {title}
        </Text>

        <Flex align="center" gap="s">
          <SvgIcon icon={<CalendarDots />} color="sand-10" size="l" />
          <Flex direction="column">
            <Text size="text-xs" weight={600}>
              Schedule
            </Text>
            <Text color="sand-12">{schedule}</Text>
          </Flex>
        </Flex>
      </Section>

      <Section>{children}</Section>

      <Section>
        <CompetitionLeaderboardTable competitionId={competitionId} />
      </Section>
    </>
  );
};
