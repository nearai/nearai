'use client';

import { CodeBlock, Play } from '@phosphor-icons/react';
import { type ReactNode } from 'react';
import { type z } from 'zod';

import { Badge } from '~/components/lib/Badge';
import { Button } from '~/components/lib/Button';
import { Card } from '~/components/lib/Card';
import { Flex } from '~/components/lib/Flex';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { StarButton } from '~/components/StarButton';
import { ENTRY_CATEGORY_LABELS, primaryUrlForEntry } from '~/lib/entries';
import { type entryModel } from '~/lib/models';

import { ConditionalLink } from './lib/ConditionalLink';
import { ImageIcon } from './lib/ImageIcon';

type Props = {
  entry: z.infer<typeof entryModel>;
  linksOpenNewTab?: boolean;
  footer?: ReactNode;
};

export const EntryCard = ({ entry, linksOpenNewTab, footer }: Props) => {
  const icon = ENTRY_CATEGORY_LABELS[entry.category]?.icon;
  const primaryUrl = primaryUrlForEntry(entry);
  const target = linksOpenNewTab ? '_blank' : undefined;

  return (
    <Card gap="m">
      <Flex gap="s" align="center">
        <ConditionalLink href={primaryUrl}>
          <ImageIcon
            src={entry.details.icon}
            alt={entry.name}
            fallbackIcon={icon}
          />
        </ConditionalLink>

        <Flex gap="none" direction="column">
          <ConditionalLink
            href={primaryUrl}
            target={target}
            style={{ zIndex: 1, position: 'relative' }}
          >
            <Text size="text-base" weight={600} color="sand-12">
              {entry.name}
            </Text>
          </ConditionalLink>

          <ConditionalLink
            href={`/profiles/${entry.namespace}`}
            target={target}
            style={{ marginTop: '-0.1rem' }}
          >
            <Text size="text-xs" weight={400}>
              @{entry.namespace}
            </Text>
          </ConditionalLink>
        </Flex>
      </Flex>

      {entry.description && <Text size="text-s">{entry.description}</Text>}

      <Flex gap="s" align="center">
        <Badge
          label={ENTRY_CATEGORY_LABELS[entry.category]?.label ?? entry.category}
          variant="neutral"
        />

        <Tooltip content="Latest Version">
          <Badge label={entry.version} variant="neutral" />
        </Tooltip>

        <StarButton entry={entry} variant="simple" />

        {entry.category === 'agent' && (
          <>
            <Tooltip asChild content="View Source">
              <Button
                label="View Source"
                icon={<CodeBlock weight="duotone" />}
                size="small"
                fill="ghost"
                target={target}
                href={`${primaryUrl}/source`}
              />
            </Tooltip>

            <Tooltip asChild content="Run Agent">
              <Button
                label="Run"
                icon={<Play weight="duotone" />}
                size="small"
                fill="ghost"
                target={target}
                href={`${primaryUrl}/run`}
              />
            </Tooltip>
          </>
        )}
      </Flex>

      {footer}
    </Card>
  );
};