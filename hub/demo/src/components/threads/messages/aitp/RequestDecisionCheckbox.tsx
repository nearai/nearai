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

import { stringToHtmlAttribute } from '~/utils/string';

import { type requestDecisionSchema } from './schema/decision';
import s from './styles.module.scss';

type Props = {
  contentId: string;
  content: z.infer<typeof requestDecisionSchema>['request_decision'];
};

export const RequestDecisionCheckbox = ({ content, contentId }: Props) => {
  if (content.type !== 'checkbox' && content.type !== 'radio') {
    console.error(
      `Attempted to render <RequestDecisionCheckbox /> with invalid content type: ${content.type}`,
    );
    return null;
  }

  const inputNameForCheckbox = (
    option: NonNullable<Props['content']['options']>[number],
    index: number,
  ) => {
    return content.type === 'checkbox'
      ? stringToHtmlAttribute(contentId + option.id + index)
      : contentId;
  };

  const submitDecision = async () => {
    // TODO
    console.log(`Selected decision via ${content.type}`);
  };

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
            <Flex as="label" key={option.id + index} gap="s" align="center">
              <Checkbox
                name={inputNameForCheckbox(option, index)}
                type={content.type === 'checkbox' ? 'checkbox' : 'radio'}
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

        <Button label="Submit" variant="affirmative" onClick={submitDecision} />
      </Flex>
    </Card>
  );
};
