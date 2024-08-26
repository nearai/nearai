'use client';

import { Fragment, useEffect, useRef } from 'react';
import { type z } from 'zod';

import { type messageModel } from '~/lib/models';

import { Card } from '../lib/Card';
import { Text } from '../lib/Text';
import s from './ChatThread.module.scss';

type Props = {
  messages: z.infer<typeof messageModel>[];
};

export const ChatThread = ({ messages }: Props) => {
  const count = messages.length;
  const element = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!element.current) return;
    const lastElement = [...element.current.children].at(-1);
    if (!lastElement) return;
    lastElement.scrollIntoView();
  }, [count]);

  return (
    <div className={s.chatThread} ref={element}>
      {messages.map((message, index) => (
        <Fragment key={index}>
          {message.role === 'user' ? (
            <Card background="sand2" style={{ alignSelf: 'end' }}>
              <Text color="sand11">{message.content}</Text>
            </Card>
          ) : (
            <Card animateIn>
              <Text color="sand12">{message.content}</Text>
              <Text size="text-xs" style={{ textTransform: 'capitalize' }}>
                - {message.role}
              </Text>
            </Card>
          )}
        </Fragment>
      ))}
    </div>
  );
};
