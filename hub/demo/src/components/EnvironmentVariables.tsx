'use client';

import { Flex, Section, Text } from '@nearai/ui';

import { useCurrentEntry } from '@/hooks/entries';
import { useQueryParams } from '@/hooks/url';
import { WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS } from '@/utils/wallet';

import { EntryEnvironmentVariables } from './EntryEnvironmentVariables';

export const EnvironmentVariables = () => {
  const { currentEntry } = useCurrentEntry('agent');
  const { queryParams } = useQueryParams([
    'showLogs',
    'threadId',
    'theme',
    'view',
    'initialUserMessage',
    'mockedAitpMessages',
    ...WALLET_TRANSACTION_CALLBACK_URL_QUERY_PARAMS,
  ]);
  if (!currentEntry) return null;
  return (
    <Section
      background="sand-2"
      style={{ borderRadius: 16, padding: 32, marginTop: 24 }}
    >
      <Flex direction="column" gap="l">
        <Text size="text-xl" weight={700}>
          Global Environment Variables
        </Text>
        <Text size="text-s" color="sand-11">
          These variables are available globally for this agent.
        </Text>
        <EntryEnvironmentVariables
          entry={currentEntry}
          excludeQueryParamKeys={Object.keys(queryParams)}
        />
      </Flex>
    </Section>
  );
};
