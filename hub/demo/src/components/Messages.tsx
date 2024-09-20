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
  const previousMessages = usePrevious(messages);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const scrolledToThreadId = useRef('');

  useEffect(() => {
    if (!messagesRef.current) return;
    const children = [...messagesRef.current.children];
    if (!children.length) return;

    const count = messages.length;
    const previousCount = previousMessages?.length;

    function scroll() {
      if (threadId !== scrolledToThreadId.current) {
        window.scrollTo(0, document.body.scrollHeight);
      } else if (previousCount < count) {
        const index = previousCount;
        children[index]?.scrollIntoView({
          block: 'start',
          behavior: 'smooth',
        });
      }

      setTimeout(() => {
        scrolledToThreadId.current = threadId;
      }, 1000);
    }

    scroll();
  }, [threadId, previousMessages, messages]);

  function determineCodeLanguageForMessage(index: number) {
    if (!index) return;
    const previousMessage = messages[index - 1];
    if (!previousMessage) return;
    const lastLine = previousMessage.content.split('\n').pop()?.trim();
    if (!lastLine) return;

    if (lastLine.startsWith('WRITE ')) return filePathToCodeLanguage(lastLine);
  }

  return (
    <div className={s.wrapper}>
      {isAuthenticated && loading ? (
        <PlaceholderCard />
      ) : (
        <>
          {welcomeMessage}
          {isAuthenticated && (
            <div className={s.messages} ref={messagesRef}>
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
            </div>
          )}
        </>
      )}
    </div>
  );
};
