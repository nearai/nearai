'use client';

import { Copy } from '@phosphor-icons/react';
import { usePrevious } from '@uidotdev/usehooks';
import { Fragment, useEffect, useRef } from 'react';
import { type z } from 'zod';

import { type messageModel } from '~/lib/models';
import { copyTextToClipboard } from '~/utils/clipboard';

import { Button } from '../lib/Button';
import { Card } from '../lib/Card';
import { Flex } from '../lib/Flex';
import { Text } from '../lib/Text';
import { Tooltip } from '../lib/Tooltip';
import s from './ChatThread.module.scss';

type Props = {
  messages: z.infer<typeof messageModel>[];
};

export const ChatThread = ({ messages }: Props) => {
  const count = messages.length;
  const previousCount = usePrevious(count);
  const element = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!element.current) return;
    const children = [...element.current.children];
    if (!children.length) return;

    if (previousCount >= count) {
      children[0]?.scrollIntoView({
        block: 'nearest',
      });
    } else {
      const newIndex = Math.min(children.length - 1, previousCount);
      children[newIndex]?.scrollIntoView({
        block: 'center',
      });
    }
  }, [count, previousCount]);

  return (
    <div className={s.chatThread} ref={element}>
      {messages.map((message, index) => (
        <Fragment key={index}>
          {message.role === 'user' ? (
            <Card animateIn background="sand-2" style={{ alignSelf: 'end' }}>
              <Text color="sand-11">{message.content}</Text>
            </Card>
          ) : (
            <Card animateIn>
              <Text size="text-s" color="sand-12">
                {message.content}
              </Text>

              <Flex align="center" gap="m">
                <Text
                  size="text-xs"
                  style={{ textTransform: 'capitalize', marginRight: 'auto' }}
                >
                  - {message.role}
                </Text>

                <Tooltip asChild content="Copy message content to clipboard">
                  <Button
                    label="Copy message to clipboard"
                    icon={<Copy />}
                    size="small"
                    fill="ghost"
                    onClick={() => copyTextToClipboard(message.content)}
                  />
                </Tooltip>
              </Flex>
            </Card>
          )}
        </Fragment>
      ))}
    </div>
  );
};
