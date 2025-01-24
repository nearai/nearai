'use client';

import { type z } from 'zod';

import { type threadMessageModel } from '~/lib/models';

import { JsonMessage } from './JsonMessage';
import { TextMessage } from './TextMessage';

type ThreadMessageProps = {
  message: z.infer<typeof threadMessageModel>;
};

export const ThreadMessage = ({ message }: ThreadMessageProps) => {
  /*
    NOTE: A message can have multiple content objects, though its extremely rare.
    Each content entry should be rendered as a separate message in the UI.
  */

  return (
    <>
      {message.content.map((content, index) => (
        <ThreadMessageContent content={content} message={message} key={index} />
      ))}
    </>
  );
};

type ThreadMessageContentProps = {
  content: z.infer<typeof threadMessageModel>['content'][number];
  message: z.infer<typeof threadMessageModel>;
};

const ThreadMessageContent = ({
  content,
  message,
}: ThreadMessageContentProps) => {
  if (content.type === 'json') {
    return <JsonMessage content={content} role={message.role} />;
  }

  return <TextMessage content={content} role={message.role} />;
};
