'use client';

import {
  Badge,
  Button,
  Card,
  Dialog,
  Flex,
  HR,
  Text,
  Tooltip,
} from '@near-pagoda/ui';
import { formatDollar } from '@near-pagoda/ui/utils';
import { ArrowUpRight, Star, StarHalf } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { getPrimaryDomainFromUrl as getCompanyNameFromUrl } from '~/utils/url';

import { type requestChoiceSchema } from './schema';
import s from './styles.module.scss';

type Props = {
  id: string;
  content: z.infer<typeof requestChoiceSchema>['request_choice'];
};

/*
  TODO:
  - Hover image popover zoom
  - Variants selection
  - Quantity selection
*/

export const RequestChoiceProducts = ({ content }: Props) => {
  const [zoomedImageUrl, setZoomedImageUrl] = useState('');

  return (
    <Card animateIn>
      {(content.title || content.description) && (
        <>
          <Flex direction="column" gap="s">
            {content.title && (
              <Text size="text-xs" weight={600} uppercase>
                {content.title}
              </Text>
            )}
            {content.description && (
              <Text color="sand-12">{content.description}</Text>
            )}
          </Flex>
          <HR />
        </>
      )}

      <div className={s.productGrid}>
        {content.options.map((option, index) => (
          <Card
            key={option.name + index}
            background="sand-0"
            border="sand-0"
            className={s.productCard}
          >
            {option.image_url && (
              <div
                className={s.productImage}
                style={{ backgroundImage: `url(${option.image_url})` }}
                onClick={() => setZoomedImageUrl(option.image_url ?? '')}
              />
            )}

            <Flex direction="column" gap="s">
              <Text weight={600} color="sand-12">
                {option.name}
              </Text>

              {(option.fiveStarRating || option.url) && (
                <Flex align="center" gap="s" wrap="wrap">
                  {option.fiveStarRating && (
                    <Tooltip
                      content={`Average${option.reviewsCount ? ` from ${option.reviewsCount}` : ''} reviews: ${option.fiveStarRating} out of 5 stars`}
                    >
                      <Badge
                        iconRight={
                          option.fiveStarRating < 3.75 ? (
                            <StarHalf weight="fill" />
                          ) : (
                            <Star weight="fill" />
                          )
                        }
                        label={
                          <Flex as="span" align="center" gap="xs">
                            <Text size="text-xs" weight={600} color="current">
                              {option.fiveStarRating}
                            </Text>
                            {option.reviewsCount && (
                              <Text size="text-xs">
                                ({option.reviewsCount})
                              </Text>
                            )}
                          </Flex>
                        }
                        variant="neutral"
                      />
                    </Tooltip>
                  )}

                  {option.url && (
                    <Tooltip
                      content={`View product on ${getCompanyNameFromUrl(option.url)}`}
                    >
                      <Button
                        label={getCompanyNameFromUrl(option.url) ?? 'Open'}
                        iconRight={<ArrowUpRight />}
                        variant="primary"
                        fill="outline"
                        size="x-small"
                        href={option.url}
                        target="_blank"
                      />
                    </Tooltip>
                  )}
                </Flex>
              )}

              {option.description && (
                <Text size="text-s">{option.description}</Text>
              )}

              {option.price_usd && (
                <Text size="text-l">{formatDollar(option.price_usd)}</Text>
              )}
            </Flex>

            <Button
              label="Add to cart"
              variant="affirmative"
              style={{ marginTop: 'auto' }}
            />
          </Card>
        ))}
      </div>

      <Dialog.Root
        open={!!zoomedImageUrl}
        onOpenChange={(open) => {
          if (!open) setZoomedImageUrl('');
        }}
      >
        <Dialog.Content
          title={
            content.options.find((o) => o.image_url === zoomedImageUrl)?.name
          }
          className="light"
          style={{ width: 'fit-content' }}
        >
          <img
            src={zoomedImageUrl}
            alt="Image of selected product"
            className={s.zoomedImage}
          />
        </Dialog.Content>
      </Dialog.Root>
    </Card>
  );
};
