'use client';

import {
  Badge,
  Button,
  Card,
  ConditionalLink,
  Flex,
  ImageIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import { CodeBlock, Play } from '@phosphor-icons/react';
import { type ReactNode } from 'react';
import { type z } from 'zod';

import { StarButton } from '@/components/StarButton';
import { ENTRY_CATEGORY_LABELS } from '@/lib/categories';
import { primaryUrlForEntry, rawFileUrlForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';

import { ForkButton } from './ForkButton';

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
            indicateParentClickable
            src={rawFileUrlForEntry(entry, entry.details.icon)}
            alt={entry.name}
            fallbackIcon={icon}
            padding={false}
          />
        </ConditionalLink>

        <Flex gap="none" direction="column">
          <Text
            href={primaryUrl}
            target={target}
            style={{ zIndex: 1, position: 'relative' }}
            size="text-base"
            weight={600}
            color="sand-12"
            decoration="none"
          >
            {entry.name}
          </Text>

          <Text
            href={`/profiles/${entry.namespace}`}
            target={target}
            style={{ marginTop: '-0.1rem' }}
            size="text-xs"
            weight={400}
            color="sand-11"
            decoration="none"
          >
            @{entry.namespace}
          </Text>
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
        <ForkButton entry={entry} variant="simple" />

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
