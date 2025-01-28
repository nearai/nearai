'use client';

import { Badge, Button, Card, Flex, HR, Text, Tooltip } from '@near-pagoda/ui';
import { formatDollar } from '@near-pagoda/ui/utils';
import { Star, StarHalf } from '@phosphor-icons/react';
import { type z } from 'zod';

import { type requestChoiceSchema } from './schema';
import s from './styles.module.scss';

type Props = {
  id: string;
  content: z.infer<typeof requestChoiceSchema>['request_choice'];
};

export const RequestChoiceProducts = ({ content }: Props) => {
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
            gap="s"
            key={option.name + index}
            background="sand-0"
            border="sand-0"
            className={s.productCard}
          >
            {option.image_url && (
              <div
                className={s.productImage}
                style={{ backgroundImage: `url(${option.image_url})` }}
              />
            )}

            <Text weight={600} color="sand-12">
              {option.name}
            </Text>

            {option.fiveStarRating && (
              <Flex align="center" gap="s" wrap="wrap">
                <Tooltip
                  content={`Average review: ${option.fiveStarRating} out of 5 stars`}
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
                          <Text size="text-xs">({option.reviewsCount})</Text>
                        )}
                      </Flex>
                    }
                    variant="neutral"
                  />
                </Tooltip>
              </Flex>
            )}

            {option.description && (
              <Text size="text-s">{option.description}</Text>
            )}

            <Text size="text-l" style={{ marginRight: 'auto' }}>
              {formatDollar(option.price_usd)}
            </Text>

            <Button
              label="Add to cart"
              variant="affirmative"
              style={{ marginTop: 'auto' }}
            />
          </Card>
        ))}
      </div>
    </Card>
  );
};
