'use client';

import { Copy } from '@phosphor-icons/react';
import { usePrevious } from '@uidotdev/usehooks';
import { Fragment, type ReactNode, useEffect, useRef } from 'react';
import { type z } from 'zod';

import { type messageModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { copyTextToClipboard } from '~/utils/clipboard';

import { Button } from './lib/Button';
import { Card } from './lib/Card';
import { Code, filePathToCodeLanguage } from './lib/Code';
import { Flex } from './lib/Flex';
import { PlaceholderCard } from './lib/Placeholder';
import { Text } from './lib/Text';
import { Tooltip } from './lib/Tooltip';
import s from './Messages.module.scss';

type Props = {
  loading?: boolean;
  messages: z.infer<typeof messageModel>[];
  threadId: string;
  welcomeMessage?: ReactNode;
};

export const Messages = ({
  loading,
  messages,
  threadId,
  welcomeMessage,
}: Props) => {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const previousThreadId = usePrevious(threadId);
  const previousMessages = usePrevious(messages);
  const element = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!element.current) return;
    const children = [...element.current.children];
    if (!children.length) return;

    const count = messages.length;
    const previousCount = previousMessages?.length;

    function scroll() {
      if (threadId !== previousThreadId) {
        window.scrollTo(0, document.body.scrollHeight);
      } else if (previousCount >= count) {
        children[0]?.scrollIntoView({
          block: 'start',
        });
      } else {
        const newIndex = Math.min(children.length - 1, previousCount);
        children[newIndex]?.scrollIntoView({
          block: 'start',
        });
      }
    }

    scroll();

    setTimeout(() => {
      scroll();
    });
  }, [threadId, previousThreadId, previousMessages, messages]);

  function determineCodeLanguageForMessage(index: number) {
    if (!index) return;
    const previousMessage = messages[index - 1];
    if (!previousMessage) return;
    const lastLine = previousMessage.content.split('\n').pop()?.trim();
    if (!lastLine) return;

    if (lastLine.startsWith('WRITE ')) return filePathToCodeLanguage(lastLine);
  }

  return (
    <div className={s.chatThread} ref={element}>
      {loading ? (
        <PlaceholderCard />
      ) : (
        <>
          {' '}
          {welcomeMessage}
          {isAuthenticated && (
            <>
              {messages.map((message, index) => (
                <Fragment key={index}>
                  {message.role === 'user' ? (
                    <Card
                      animateIn
                      background="sand-2"
                      style={{ alignSelf: 'end' }}
                    >
                      <Text color="sand-11">{message.content}</Text>
                    </Card>
                  ) : (
                    <Card animateIn>
                      {determineCodeLanguageForMessage(index) ? (
                        <Code
                          bleed
                          source={message.content}
                          language={determineCodeLanguageForMessage(index)}
                        />
                      ) : (
                        <Text color="sand-12">{message.content}</Text>
                      )}

                      <Flex align="center" gap="m">
                        <Text
                          size="text-xs"
                          style={{
                            textTransform: 'capitalize',
                            marginRight: 'auto',
                          }}
                        >
                          - {message.role}
                        </Text>

                        <Tooltip
                          asChild
                          content="Copy message content to clipboard"
                        >
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
            </>
          )}
        </>
      )}
    </div>
  );
};
