'use client';

import { Copy, DotsThree, Eye, MarkdownLogo } from '@phosphor-icons/react';
import { usePrevious } from '@uidotdev/usehooks';
import { Fragment, type ReactNode, useEffect, useRef, useState } from 'react';
import { type z } from 'zod';

import { type messageModel, type threadMessageModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { copyTextToClipboard } from '~/utils/clipboard';

import { Button } from './lib/Button';
import { Card } from './lib/Card';
import { Dropdown } from './lib/Dropdown';
import { Flex } from './lib/Flex';
import { Markdown } from './lib/Markdown';
import { SvgIcon } from './lib/SvgIcon';
import { Text } from './lib/Text';
import s from './Messages.module.scss';

type Props = {
  grow?: boolean;
  messages:
    | z.infer<typeof messageModel>[]
    | z.infer<typeof threadMessageModel>[];
  threadId: string;
  welcomeMessage?: ReactNode;
};

export const Messages = ({
  grow = true,
  messages,
  threadId,
  welcomeMessage,
}: Props) => {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const previousMessages = usePrevious(messages);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const scrolledToThreadId = useRef('');
  const [renderAsMarkdown, setRenderAsMarkdown] = useState(true);

  useEffect(() => {
    if (!messagesRef.current) return;
    const children = [...messagesRef.current.children];
    if (!children.length) return;

    const count = messages.length;
    const previousCount = previousMessages?.length;

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

        setTimeout(() => {
          scrolledToThreadId.current = threadId;
        }, 1000);
      }, 10);
    }

    scroll();
  }, [threadId, previousMessages, messages]);

  const normalizedMessages: z.infer<typeof messageModel>[] = messages.map(
    (message) => {
      if ('thread_id' in message) {
        return {
          content: message.content[0]?.text.value ?? '',
          role: message.role,
        };
      }

      return message;
    },
  );

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
        {normalizedMessages.map((message, index) => (
          <Fragment key={index + message.role}>
            {message.role === 'user' ? (
              <Card animateIn background="sand-2" style={{ alignSelf: 'end' }}>
                {renderAsMarkdown ? (
                  <Markdown content={message.content} />
                ) : (
                  <Text>{message.content}</Text>
                )}
              </Card>
            ) : (
              <Card animateIn>
                {renderAsMarkdown ? (
                  <Markdown content={message.content} />
                ) : (
                  <Text>{message.content}</Text>
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

                  <Dropdown.Root>
                    <Dropdown.Trigger asChild>
                      <Button
                        label="Message Actions"
                        icon={<DotsThree weight="bold" />}
                        size="x-small"
                        fill="ghost"
                      />
                    </Dropdown.Trigger>

                    <Dropdown.Content sideOffset={0}>
                      <Dropdown.Section>
                        <Dropdown.Item
                          onSelect={() => copyTextToClipboard(message.content)}
                        >
                          <SvgIcon icon={<Copy />} />
                          Copy To Clipboard
                        </Dropdown.Item>

                        {renderAsMarkdown ? (
                          <Dropdown.Item
                            onSelect={() => setRenderAsMarkdown(false)}
                          >
                            <SvgIcon icon={<MarkdownLogo />} />
                            View Markdown Source
                          </Dropdown.Item>
                        ) : (
                          <Dropdown.Item
                            onSelect={() => setRenderAsMarkdown(true)}
                          >
                            <SvgIcon icon={<Eye />} />
                            Render Markdown
                          </Dropdown.Item>
                        )}
                      </Dropdown.Section>
                    </Dropdown.Content>
                  </Dropdown.Root>
                </Flex>
              </Card>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
};
