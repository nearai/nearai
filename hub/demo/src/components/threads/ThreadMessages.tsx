'use client';

import { usePrevious } from '@uidotdev/usehooks';
import { type ReactNode, useEffect, useRef } from 'react';
import { type z } from 'zod';

import { type threadMessageModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';

import { computeNavigationHeight } from '../Navigation';
import { JsonMessage } from './messages/JsonMessage';
import { TextMessage } from './messages/TextMessage';
import s from './ThreadMessages.module.scss';

type Props = {
  grow?: boolean;
  messages: z.infer<typeof threadMessageModel>[];
  scrollTo?: boolean;
  threadId: string;
  welcomeMessage?: ReactNode;
};

function totalMessagesAndContents(
  messages: z.infer<typeof threadMessageModel>[],
) {
  return (
    messages?.reduce((total, message) => total + message.content.length, 0) ?? 0
  );
}

export const ThreadMessages = ({
  grow = true,
  messages,
  scrollTo = true,
  threadId,
  welcomeMessage,
}: Props) => {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const previousMessages = usePrevious(messages);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const scrolledToThreadId = useRef('');

  useEffect(() => {
    if (!messagesRef.current) return;
    const children = [...messagesRef.current.children];
    if (!children.length) return;

    const count = totalMessagesAndContents(messages);
    const previousCount = totalMessagesAndContents(previousMessages);

    function scroll() {
      setTimeout(() => {
        if (threadId !== scrolledToThreadId.current) {
          window.scrollTo(0, document.body.scrollHeight);
        } else if (previousCount > 0 && previousCount < count) {
          const previousChild = children[previousCount - 1];

          if (previousChild) {
            const offset = computeNavigationHeight();
            const y =
              previousChild.getBoundingClientRect().bottom +
              window.scrollY -
              offset;
            window.scrollTo({ top: y, behavior: 'smooth' });
          }
        }

        scrolledToThreadId.current = threadId;
      }, 10);
    }

    if (scrollTo) {
      scroll();
    }
  }, [threadId, previousMessages, messages, scrollTo]);

  if (!isAuthenticated) {
    return (
      <div className={s.wrapper} data-grow={grow}>
        {welcomeMessage}
      </div>
    );
  }

  return (
    <div className={s.wrapper} data-grow={grow}>
      {welcomeMessage}

      <div className={s.messages} ref={messagesRef}>
        {messages.map((message, index) => (
          <ThreadMessage message={message} key={index + message.role} />
        ))}
      </div>
    </div>
  );
};

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
        <ThreadMessageContent
          content={content}
          contentIndex={index}
          message={message}
          key={index}
        />
      ))}
    </>
  );
};

type ThreadMessageContentProps = {
  content: z.infer<typeof threadMessageModel>['content'][number];
  contentIndex: number;
  message: z.infer<typeof threadMessageModel>;
};

const ThreadMessageContent = ({
  content,
  contentIndex,
  message,
}: ThreadMessageContentProps) => {
  const id = `${message.id}_${contentIndex}`;

  if (content.type === 'json') {
    return <JsonMessage id={id} content={content} role={message.role} />;
  }

  return <TextMessage id={id} content={content} role={message.role} />;
};
