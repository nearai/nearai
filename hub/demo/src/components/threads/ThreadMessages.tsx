'use client';

import { usePrevious } from '@uidotdev/usehooks';
import { type ReactNode, useEffect, useRef } from 'react';
import { type z } from 'zod';

import { type threadMessageModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';

import { ThreadMessage } from './ThreadMessage';
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
  return messages.reduce((total, message) => total + message.content.length, 0);
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
        } else if (previousCount < count) {
          const index = previousCount;
          children[index]?.scrollIntoView({
            block: 'start',
            behavior: 'smooth',
          });
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
