'use client';

import { Accordion, Flex, SvgIcon, Text } from '@nearai/ui';
import { ChatCircleDots } from '@phosphor-icons/react';
import {
  Fragment,
  memo,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react';
import { type z } from 'zod';

import { useConsumerModeEnabled } from '@/hooks/consumer';
import type { ExtendedMessage } from '@/hooks/threads';
import { type MessageGroup, useGroupedThreadMessages } from '@/hooks/threads';
import { type threadMessageModel } from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { stringToPotentialJson } from '@/utils/string';

import { computeNavigationHeight } from '../Navigation';
import { JsonMessage } from './messages/JsonMessage';
import { TextMessage } from './messages/TextMessage';
import { UnknownMessage } from './messages/UnknownMessage';
import { ThreadMessageContentProvider } from './ThreadMessageContentProvider';
import s from './ThreadMessages.module.scss';

type Props = {
  grow?: boolean;
  messages: z.infer<typeof threadMessageModel>[];
  scroll?: boolean;
  streamingText?: string;
  streamingTextLatestChunk?: string;
  threadId: string;
  welcomeMessage?: ReactNode;
};

export const ThreadMessages = ({
  grow = true,
  messages,
  scroll = true,
  streamingText,
  threadId,
  welcomeMessage,
  streamingTextLatestChunk,
}: Props) => {
  const auth = useAuthStore((store) => store.auth);
  const scrolledToThreadId = useRef('');
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const countRef = useRef(0);
  const previousCountRef = useRef(0);
  const { groupedMessages } = useGroupedThreadMessages(messages, streamingText);

  useEffect(() => {
    if (streamingTextLatestChunk && scroll) {
      window.scrollTo(0, document.body.scrollHeight);
    }
  }, [streamingTextLatestChunk, scroll]);

  useEffect(() => {
    if (!messagesRef.current) return;
    const children = [...messagesRef.current.children];
    if (!children.length) return;

    function scrollScreen() {
      setTimeout(() => {
        countRef.current = children.length;

        if (threadId !== scrolledToThreadId.current) {
          window.scrollTo(0, document.body.scrollHeight);
        } else if (
          previousCountRef.current > 0 &&
          previousCountRef.current < countRef.current
        ) {
          const previousChild = children[previousCountRef.current - 1];

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
        previousCountRef.current = countRef.current;
      }, 10);
    }

    if (scroll) {
      scrollScreen();
    }
  }, [groupedMessages, threadId, scroll]);

  if (!auth) {
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
        {groupedMessages.map((group, groupIndex) => (
          <Fragment key={groupIndex}>
            {group.isRootThread ? (
              <>
                {group.messages.map((message, messageIndex) => (
                  <ThreadMessage message={message} key={messageIndex} />
                ))}
              </>
            ) : (
              <Subthread group={group} />
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
};

type SubthreadProps = {
  group: MessageGroup;
};

const Subthread = ({ group }: SubthreadProps) => {
  const { consumerModeEnabled } = useConsumerModeEnabled();
  const [accordionValue, setAccordionValue] = useState<string[]>();

  if (consumerModeEnabled) {
    // As of now, we don't want to show subthreads to end users within chat.near.ai
    return null;
  }

  return (
    <div className={s.subthread}>
      <Accordion.Root
        type="multiple"
        value={accordionValue}
        onValueChange={setAccordionValue}
      >
        <Accordion.Item value="subthread">
          <Accordion.Trigger style={{ width: 'auto', gap: 'var(--gap-s)' }}>
            <Flex
              align="center"
              gap="s"
              style={{ paddingBlock: 'var(--gap-s)' }}
            >
              <SvgIcon
                icon={<ChatCircleDots weight="fill" />}
                color="sand-10"
                size="xs"
              />
              <Text size="text-xs" weight={500} color="current">
                {accordionValue?.includes('subthread') ? 'Collapse' : 'Expand'}{' '}
                {group.messages.length} subthread message
                {group.messages.length !== 1 ? 's' : ''}
              </Text>
            </Flex>
          </Accordion.Trigger>

          <Accordion.Content style={{ paddingBottom: 0 }}>
            {group.messages.map((message, messageIndex) => (
              <ThreadMessage message={message} key={messageIndex} />
            ))}

            <Text
              size="text-2xs"
              family="monospace"
              style={{ marginLeft: 'auto' }}
            >
              {group.threadId}
            </Text>
          </Accordion.Content>
        </Accordion.Item>
      </Accordion.Root>
    </div>
  );
};

type ThreadMessageProps = {
  message: ExtendedMessage;
};

const ThreadMessage = ({ message }: ThreadMessageProps) => {
  /*
    NOTE: A message can have multiple content objects, though its extremely rare.
    Each content entry should be rendered as a separate message in the UI.
  */

  return (
    <>
      {message.content.map((content, index) => (
        <ThreadMessageContent
          content={content}
          message={message}
          messageContentId={`${message.id}_${index}`}
          key={index}
        />
      ))}
    </>
  );
};

type ThreadMessageContentProps = {
  content: z.infer<typeof threadMessageModel>['content'][number];
  message: ExtendedMessage;
  messageContentId: string;
};

const ThreadMessageContent = memo(
  ({ content, messageContentId, message }: ThreadMessageContentProps) => {
    const providerValue = {
      content,
      message,
      messageContentId,
    };

    const text = typeof content.text === 'object' ? content.text : null;
    const json = text?.value ? stringToPotentialJson(text.value) : null;

    if (json) {
      return (
        <ThreadMessageContentProvider value={providerValue}>
          <JsonMessage json={json} />
        </ThreadMessageContentProvider>
      );
    }

    if (text) {
      return (
        <ThreadMessageContentProvider value={providerValue}>
          <TextMessage text={text} />
        </ThreadMessageContentProvider>
      );
    }

    return (
      <ThreadMessageContentProvider value={providerValue}>
        <UnknownMessage />
      </ThreadMessageContentProvider>
    );
  },
  (oldProps, newProps) => oldProps.message.id === newProps.message.id, // https://react.dev/reference/react/memo
);

ThreadMessageContent.displayName = 'ThreadMessageContent';
