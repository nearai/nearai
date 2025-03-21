'use client';

import {
  Button,
  Checkbox,
  CheckboxGroup,
  Flex,
  Form,
  openToast,
  Text,
} from '@nearai/ui';
import { type SubmitHandler, useForm } from 'react-hook-form';
import { type z } from 'zod';

import { useThreadsStore } from '@/stores/threads';
import { stringToHtmlAttribute } from '@/utils/string';

import { useThreadMessageContent } from '../../ThreadMessageContentProvider';
import { Message } from './Message';
import {
  CURRENT_AITP_DECISIONS_SCHEMA_URL,
  type decisionSchema,
  type requestDecisionSchema,
} from './schema/decisions';
import s from './styles.module.scss';

type Props = {
  content: z.infer<typeof requestDecisionSchema>['request_decision'];
};

type FormSchema = Record<string, string | boolean>;

export const RequestDecisionCheckbox = ({ content }: Props) => {
  const { messageContentId } = useThreadMessageContent();
  const hookForm = useForm<FormSchema>();
  const addMessage = useThreadsStore((store) => store.addMessage);

  const inputNameForCheckbox = (
    option: NonNullable<Props['content']['options']>[number],
    index: number,
  ) => {
    return content.type === 'checkbox'
      ? stringToHtmlAttribute(`${messageContentId}_${option.id}_${index}`)
      : messageContentId;
  };

  const onSubmit: SubmitHandler<FormSchema> = async (data) => {
    if (!addMessage) return;

    const result: z.infer<typeof decisionSchema> = {
      $schema: CURRENT_AITP_DECISIONS_SCHEMA_URL,
      decision: {
        request_decision_id: content.id,
        options: [],
      },
    };

    if (content.type === 'checkbox') {
      content.options.forEach((option, index) => {
        const value = data[inputNameForCheckbox(option, index)];

        if (value && typeof value === 'string') {
          result.decision.options.push({
            id: option.id,
            name: option.name,
          });
        }
      });
    } else {
      const value = Object.values(data)[0];
      if (value && typeof value === 'string') {
        const option = content.options.find((o) => o.id === value);
        if (option) {
          result.decision.options.push({
            id: option.id,
            name: option.name,
          });
        }
      }
    }

    if (result.decision.options.length > 0) {
      void addMessage({
        new_message: JSON.stringify(result),
      });
    } else {
      openToast({
        type: 'error',
        title: 'Please select an option',
      });
    }
  };

  if (content.type !== 'checkbox' && content.type !== 'radio') {
    console.error(
      `Attempted to render <RequestDecisionCheckbox /> with invalid content type: ${content.type}`,
    );
    return null;
  }

  return (
    <Message>
      <Form onSubmit={hookForm.handleSubmit(onSubmit)}>
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
                  type={content.type === 'checkbox' ? 'checkbox' : 'radio'}
                  value={option.id}
                  {...hookForm.register(inputNameForCheckbox(option, index))}
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

          <Button label="Submit" variant="affirmative" type="submit" />
        </Flex>
      </Form>
    </Message>
  );
};
