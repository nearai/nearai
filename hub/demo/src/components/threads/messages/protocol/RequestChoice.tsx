'use client';

import {
  Button,
  Card,
  Checkbox,
  CheckboxGroup,
  Flex,
  Text,
} from '@near-pagoda/ui';
import { type z } from 'zod';

import { RequestChoiceConfirmation } from './RequestChoiceConfirmation';
import { RequestChoiceProducts } from './RequestChoiceProducts';
import { type requestChoiceSchema } from './schema';
import s from './styles.module.scss';

type Props = {
  contentId: string;
  content: z.infer<typeof requestChoiceSchema>['request_choice'];
};

export const RequestChoice = ({ content, contentId }: Props) => {
  const type = content.type;

  const product = content.options?.find(
    (option) => typeof option.price_usd === 'number',
  );
  if (product) type === 'products';

  if (type === 'products') {
    return <RequestChoiceProducts content={content} contentId={contentId} />;
  }

  if (type === 'confirmation') {
    return (
      <RequestChoiceConfirmation content={content} contentId={contentId} />
    );
  }

  return (
    <Card animateIn>
      <Flex direction="column" gap="m" align="start">
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

        <CheckboxGroup aria-label={content.title || content.description}>
          {content.options?.map((option, index) => (
            <Flex as="label" key={option.name + index} gap="s" align="center">
              <Checkbox
                name={type === 'checkbox' ? option.name + index : contentId}
                type={type === 'checkbox' ? 'checkbox' : 'radio'}
              />

              {option.image_url && (
                <div
                  className={s.optionImage}
                  style={{ backgroundImage: `url(${option.image_url})` }}
                />
              )}

              <Flex direction="column" gap="none">
                <Text color="sand-12" weight={600}>
                  {option.name}
                </Text>

                {option.description && (
                  <Text size="text-s">{option.description}</Text>
                )}
              </Flex>
            </Flex>
          ))}
        </CheckboxGroup>

        <Button label="Submit" variant="affirmative" />
      </Flex>
    </Card>
  );
};
