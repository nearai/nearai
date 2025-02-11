'use client';

import {
  Button,
  Card,
  Dialog,
  Dropdown,
  Flex,
  SvgIcon,
  Text,
  Tooltip,
} from '@near-pagoda/ui';
import { formatDollar } from '@near-pagoda/ui/utils';
import { Star, StarHalf } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { getPrimaryDomainFromUrl } from '~/utils/url';

import { type requestDecisionSchema } from './schema/decision';
import s from './styles.module.scss';

type Props = {
  content: z.infer<typeof requestDecisionSchema>['request_decision'];
  contentId: string;
};

export const RequestDecisionProducts = ({ content, contentId }: Props) => {
  if (content.type !== 'products') {
    console.error(
      `Attempted to render <RequestDecisionProducts /> with invalid content type: ${content.type}`,
    );
    return null;
  }

  return (
    <Card animateIn>
      {(content.title || content.description) && (
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
      )}

      <div className={s.productGrid}>
        {content.options?.map((option, index) => (
          <Product
            contentId={contentId}
            index={index}
            option={option}
            key={option.id + index}
          />
        ))}
      </div>
    </Card>
  );
};

type Product = {
  contentId: string;
  index: number;
  option: NonNullable<
    z.infer<typeof requestDecisionSchema>['request_decision']['options']
  >[number];
};

const quantities = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const Product = (props: Product) => {
  const [zoomedImageUrl, setZoomedImageUrl] = useState('');

  const variants = [...(props.option.variants ?? [])];
  if (!variants.find((v) => v.name == props.option.name)) {
    variants.unshift(props.option);
  }
  const hasVariants = variants.length >= 2;
  const [selectedVariantName, setSelectedVariantName] = useState(
    props.option.name,
  );
  const [quantity, setQuantity] = useState(1);

  const option = {
    ...props.option,
    ...variants.find((v) => v.name === selectedVariantName),
  };

  const priceUsd = option.quote?.payment_plans.find(
    (p) => p.plan_type === 'one-time' && p.currency === 'USD',
  );

  const addProductToCart = async () => {
    // TODO
    console.log(`Selected product with quantity: ${quantity}`, option);
  };

  const displayName = option.short_variant_name || option.name || option.id;

  return (
    <Card background="sand-0" border="sand-0" className={s.productCard}>
      {option.image_url && (
        <div
          className={s.productImage}
          style={{ backgroundImage: `url(${option.image_url})` }}
          onClick={() => setZoomedImageUrl(option.image_url ?? '')}
        />
      )}

      <Flex direction="column" gap="xs" align="start">
        <Tooltip
          content={`View product on ${getPrimaryDomainFromUrl(option.url)}`}
          asChild
        >
          <Text
            weight={600}
            color={option.url ? undefined : 'sand-12'}
            href={option.url}
            decoration="none"
            target="_blank"
            style={{ lineHeight: 1.35 }}
          >
            {option.name}
          </Text>
        </Tooltip>

        <FiveStarRating option={option} />
      </Flex>

      {option.description && <Text size="text-s">{option.description}</Text>}

      <Flex direction="column" gap="m" style={{ marginTop: 'auto' }}>
        {priceUsd && (
          <Text
            size="text-l"
            style={{ lineHeight: 1, marginBottom: '-0.25rem' }}
          >
            {formatDollar(priceUsd.amount)}
          </Text>
        )}

        <Flex align="center" gap="s">
          {hasVariants && (
            <Dropdown.Root>
              <Dropdown.Trigger asChild>
                <Button
                  label={displayName}
                  labelAlignment="left"
                  variant="secondary"
                  fill="outline"
                  iconRight={<Dropdown.Indicator />}
                  size="small"
                  style={{ flexGrow: 1, flexShrink: 1 }}
                />
              </Dropdown.Trigger>

              <Dropdown.Content style={{ maxWidth: '20rem' }}>
                <Dropdown.Section>
                  {variants.map((variant, index) => (
                    <Dropdown.Item
                      key={variant.id + index}
                      onSelect={() => setSelectedVariantName(variant.name)}
                    >
                      <Flex align="center" gap="s">
                        {variant.image_url && (
                          <div
                            className={s.variantOptionImage}
                            style={{
                              backgroundImage: `url(${variant.image_url})`,
                            }}
                          />
                        )}
                        {displayName}
                      </Flex>
                    </Dropdown.Item>
                  ))}
                </Dropdown.Section>
              </Dropdown.Content>
            </Dropdown.Root>
          )}

          <Dropdown.Root>
            <Dropdown.Trigger asChild>
              <Button
                label={
                  hasVariants ? quantity.toString() : `Quantity: ${quantity}`
                }
                labelAlignment="left"
                variant="secondary"
                fill="outline"
                iconRight={<Dropdown.Indicator />}
                size="small"
                style={hasVariants ? undefined : { flexGrow: 1 }}
              />
            </Dropdown.Trigger>

            <Dropdown.Content style={{ minWidth: 'auto' }}>
              <Dropdown.Section>
                <Dropdown.SectionContent>
                  <Text weight={600} size="text-xs" uppercase>
                    Quantity
                  </Text>
                </Dropdown.SectionContent>

                {quantities.map((q) => (
                  <Dropdown.Item
                    key={q}
                    onSelect={() => setQuantity(q)}
                    style={{ justifyContent: 'center' }}
                  >
                    {q}
                  </Dropdown.Item>
                ))}
              </Dropdown.Section>
            </Dropdown.Content>
          </Dropdown.Root>
        </Flex>

        <Button
          label="Add to cart"
          variant="affirmative"
          size="small"
          onClick={addProductToCart}
        />
      </Flex>

      <Dialog.Root
        open={!!zoomedImageUrl}
        onOpenChange={(open) => {
          if (!open) setZoomedImageUrl('');
        }}
      >
        <Dialog.Content
          title={option.name}
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

type FiveStarRatingProps = {
  option: NonNullable<
    z.infer<typeof requestDecisionSchema>['request_decision']['options']
  >[number];
};

const FiveStarRating = ({ option }: FiveStarRatingProps) => {
  const { five_star_rating: fiveStarRating, reviews_count: reviewsCount = 0 } =
    option;

  if (typeof fiveStarRating != 'number') return null;

  return (
    <Tooltip
      content={`Average ${reviewsCount ? `from ${reviewsCount} review${reviewsCount !== 1 ? 's' : ''}` : 'review'}: ${fiveStarRating} out of 5 stars`}
    >
      <Flex align="center" gap="xs">
        <SvgIcon
          icon={
            fiveStarRating > 0.95 ? (
              <Star weight="fill" />
            ) : fiveStarRating > 0.45 ? (
              <StarHalf weight="fill" />
            ) : (
              <Star weight="light" color="sand-6" />
            )
          }
          size="xs"
        />

        <SvgIcon
          icon={
            fiveStarRating > 1.95 ? (
              <Star weight="fill" />
            ) : fiveStarRating > 1.45 ? (
              <StarHalf weight="fill" />
            ) : (
              <Star weight="light" color="sand-6" />
            )
          }
          size="xs"
        />

        <SvgIcon
          icon={
            fiveStarRating > 2.95 ? (
              <Star weight="fill" />
            ) : fiveStarRating > 2.45 ? (
              <StarHalf weight="fill" />
            ) : (
              <Star weight="light" color="sand-6" />
            )
          }
          size="xs"
        />

        <SvgIcon
          icon={
            fiveStarRating > 3.95 ? (
              <Star weight="fill" />
            ) : fiveStarRating > 3.45 ? (
              <StarHalf weight="fill" />
            ) : (
              <Star weight="light" color="sand-6" />
            )
          }
          size="xs"
        />

        <SvgIcon
          icon={
            fiveStarRating > 4.95 ? (
              <Star weight="fill" />
            ) : fiveStarRating > 4.45 ? (
              <StarHalf weight="fill" />
            ) : (
              <Star weight="light" />
            )
          }
          size="xs"
        />

        {reviewsCount ? <Text size="text-s">({reviewsCount})</Text> : null}
      </Flex>
    </Tooltip>
  );
};
