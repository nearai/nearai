import { useCallback, useMemo, useRef } from 'react';
import { type z } from 'zod';

import { type threadMessageModel, type threadModel } from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { type AppRouterOutputs } from '@/trpc/router';
import { trpc } from '@/trpc/TRPCProvider';

import { useEmbeddedWithinIframe } from './embed';
import { useCurrentEntry, useCurrentEntryParams } from './entries';
import { useQueryParams } from './url';

export type ThreadSummary = z.infer<typeof threadModel> & {
  agent: {
    name: string;
    namespace: string;
    version: string;
    url: string;
  };
  lastMessageAt: Date | null;
  messageCount: number;
  url: string;
};

export function useThreads() {
  const { embedded } = useEmbeddedWithinIframe();
  const currentEntryParams = useCurrentEntryParams();
  const auth = useAuthStore((store) => store.auth);
  const utils = trpc.useUtils();

  const threadsQuery = trpc.hub.threads.useQuery(undefined, {
    enabled: !!auth,
  });

  const setThreadData = useCallback(
    (id: string, data: Partial<AppRouterOutputs['hub']['threads'][number]>) => {
      const threads = [...(threadsQuery.data ?? [])].map((thread) => {
        if (thread.id === id) {
          return {
            ...thread,
            ...data,
          };
        }

        return thread;
      });

      utils.hub.threads.setData(undefined, threads);
    },
    [utils, threadsQuery.data],
  );

  const threads = useMemo(() => {
    if (!auth) return [];
    if (!threadsQuery.data) return;

    const result: ThreadSummary[] = [];

    for (const data of threadsQuery.data) {
      const rootAgentId = data.metadata.agent_ids?.[0];
      if (!rootAgentId) continue;

      const [namespace, name, version, ...otherSegments] =
        rootAgentId.split('/');
      if (!namespace || !name || !version || otherSegments.length > 0) continue;

      if (
        embedded &&
        (currentEntryParams.namespace !== namespace ||
          currentEntryParams.name !== name)
      ) {
        // When embedded within an iframe, only show threads for the embedded agent
        continue;
      }

      const agentUrl = `/agents/${namespace}/${name}/${version}`;
      const threadUrl = `${agentUrl}/run?threadId=${encodeURIComponent(data.id)}`;

      result.push({
        ...data,
        metadata: {
          ...data.metadata,
          topic: data.metadata.topic || name,
        },
        agent: {
          name,
          namespace,
          version,
          url: agentUrl,
        },
        lastMessageAt: new Date(),
        messageCount: 0,
        url: threadUrl,
      });
    }

    return result;
  }, [
    auth,
    threadsQuery.data,
    embedded,
    currentEntryParams.name,
    currentEntryParams.namespace,
  ]);

  return {
    setThreadData,
    threads,
    threadsQuery,
  };
}

export type ExtendedMessage = z.infer<typeof threadMessageModel> & {
  streamed?: boolean;
};

export type MessageGroup = {
  isRootThread: boolean;
  threadId: string;
  messages: ExtendedMessage[];
};

export function useGroupedThreadMessages(
  messages: z.infer<typeof threadMessageModel>[],
  streamingText?: string,
) {
  const { queryParams } = useQueryParams(['threadId']);
  const rootThreadId = queryParams.threadId!;
  const streamingTextRef = useRef('');
  const { currentEntry } = useCurrentEntry('agent', {
    refetchOnMount: false,
  });
  const showStreamingMessage =
    currentEntry?.details.agent?.show_streaming_message;

  const groupedMessages = useMemo(() => {
    const result: MessageGroup[] = [];

    messages.forEach((message) => {
      const latestGroup = result.length > 0 ? result.at(-1) : undefined;

      if (latestGroup?.threadId === message.thread_id) {
        latestGroup.messages.push(message);
        return;
      } else {
        result.push({
          isRootThread:
            message.thread_id === rootThreadId ||
            message.thread_id === '' ||
            !rootThreadId,
          threadId: message.thread_id,
          messages: [message],
        });
      }
    });

    const lastMessage = result.at(-1)?.messages.at(-1);
    if (
      lastMessage &&
      streamingText &&
      lastMessage.content
        .at(-1)
        ?.text?.value.startsWith(streamingTextRef.current)
    ) {
      lastMessage.streamed = true;
    }

    if (streamingText && showStreamingMessage) {
      streamingTextRef.current = streamingText;

      result.push({
        isRootThread: true,
        threadId: rootThreadId,
        messages: [
          {
            attachments: [],
            content: [
              {
                type: 'text',
                text: {
                  value: streamingText,
                  annotations: [],
                },
              },
            ],
            completed_at: Date.now(),
            created_at: Date.now(),
            id: crypto.randomUUID(),
            incomplete_at: null,
            object: '',
            role: 'assistant',
            run_id: null,
            status: 'completed',
            thread_id: rootThreadId,
          },
        ],
      });
    } else {
      streamingTextRef.current = '';
    }

    return result;
  }, [messages, rootThreadId, streamingText, showStreamingMessage]);

  return {
    groupedMessages,
  };
}
