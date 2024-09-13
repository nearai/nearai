'use client';

import { CodeBlock, Play } from '@phosphor-icons/react';
import Link from 'next/link';
import { type z } from 'zod';

import { Badge } from '~/components/lib/Badge';
import { Button } from '~/components/lib/Button';
import { Card } from '~/components/lib/Card';
import { Flex } from '~/components/lib/Flex';
import { Text } from '~/components/lib/Text';
import { Tooltip } from '~/components/lib/Tooltip';
import { StarButton } from '~/components/StarButton';
import { type registryEntry } from '~/lib/models';
import { CATEGORY_LABELS } from '~/utils/category';

import { ImageIcon } from './lib/ImageIcon';

type Props = {
  item: z.infer<typeof registryEntry>;
};

export const ResourceCard = ({ item }: Props) => {
  const icon = CATEGORY_LABELS[item.category]?.icon;
  const baseUrl = `/agents/${item.namespace}/${item.name}/${item.version}`;

  return (
    <Card gap="m">
      <Flex gap="s" align="center">
        <Link href={baseUrl}>
          <ImageIcon
            src={item.details.icon}
            alt={item.name}
            fallbackIcon={icon}
          />
        </Link>

        <Flex gap="none" direction="column">
          <Link href={baseUrl} style={{ zIndex: 1, position: 'relative' }}>
            <Text size="text-base" weight={600} color="sand-12">
              {item.name}
            </Text>
          </Link>

          <Link
            href={`/profiles/${item.namespace}`}
            style={{ marginTop: '-0.4rem' }}
          >
            <Text size="text-xs" weight={400}>
              @{item.namespace}
            </Text>
          </Link>
        </Flex>
      </Flex>

      {item.description && <Text size="text-s">{item.description}</Text>}

      <Flex gap="s" align="center">
        <Badge
          label={CATEGORY_LABELS[item.category]?.label ?? item.category}
          variant="neutral"
        />

        <Tooltip content="Latest Version">
          <Badge label={item.version} variant="neutral" />
        </Tooltip>

        <StarButton item={item} variant="simple" />

        {item.category === 'agent' && (
          <>
            <Tooltip asChild content="View Source">
              <Button
                label="View Source"
                icon={<CodeBlock weight="duotone" />}
                size="small"
                fill="ghost"
                href={`${baseUrl}/source`}
              />
            </Tooltip>

            <Tooltip asChild content="Run Agent">
              <Button
                label="Run"
                icon={<Play weight="duotone" />}
                size="small"
                fill="ghost"
                href={`${baseUrl}/run`}
              />
            </Tooltip>
          </>
        )}
      </Flex>
    </Card>
  );
};
