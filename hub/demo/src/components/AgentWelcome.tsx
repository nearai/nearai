'use client';

import { Flex, ImageIcon, Text } from '@nearai/ui';
import { type z } from 'zod';

import { ENTRY_CATEGORY_LABELS } from '@/lib/categories';
import { rawFileUrlForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';

import { Markdown } from './lib/Markdown';

type Props = {
  currentEntry: z.infer<typeof entryModel>;
};

export const AgentWelcome = ({ currentEntry }: Props) => {
  const welcome = currentEntry.details.agent?.welcome;

  if (!welcome) return null;

  return (
    <Flex
      direction="column"
      gap="m"
      style={{
        marginTop: 'auto',
      }}
    >
      <Flex align="center" gap="m">
        <ImageIcon
          size="l"
          src={rawFileUrlForEntry(
            currentEntry,
            welcome.icon || currentEntry.details.icon,
          )}
          alt={currentEntry.name}
          fallbackIcon={ENTRY_CATEGORY_LABELS.agent.icon}
          padding={false}
        />
        <Text size="text-l">{welcome.title || currentEntry.name}</Text>
      </Flex>

      {welcome.description && (
        <Flex
          direction="column"
          gap="m"
          style={{
            borderImageSource:
              'linear-gradient(to bottom, var(--green-9), var(--violet-9))',
            borderImageSlice: 1,
            borderLeft: '2px solid',
            paddingLeft: 'calc((var(--icon-size-l) / 2) + var(--gap-m))',
            marginLeft: 'calc(var(--icon-size-l) / 2)',
          }}
        >
          <Markdown content={welcome.description} />
        </Flex>
      )}
    </Flex>
  );
};
