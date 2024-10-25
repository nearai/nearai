import { useCallback, useMemo } from 'react';
import { type z } from 'zod';

import { type threadModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api, type RouterOutputs } from '~/trpc/react';

export type Thread = z.infer<typeof threadModel> & {
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
  const accountId = useAuthStore((store) => store.auth?.account_id);
  const utils = api.useUtils();

  const threadsQuery = api.hub.threads.useQuery(undefined, {
    enabled: !!accountId,
  });
  // const entriesQuery = api.hub.entries.useQuery(
  //   {
  //     category: 'environment',
  //     namespace: accountId,
  //   },
  //   {
  //     enabled: !!accountId,
  //   },
  // );

  const setThreadData = useCallback(
    (id: string, data: Partial<RouterOutputs['hub']['threads'][number]>) => {
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
    if (!accountId) return [];
    if (!threadsQuery.data) return;

    const result: Thread[] = [];

    for (const data of threadsQuery.data) {
      if (!data.metadata.root_agent) continue;

      const { name, namespace, version } = data.metadata.root_agent;

      const agentUrl = `/agents/${namespace}/${name}/${version}`;
      const threadUrl = `${agentUrl}/run?threadId=${encodeURIComponent(data.id)}`;

      result.push({
        ...data,
        metadata: {
          ...data.metadata,
          // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
          topic: data.metadata.topic || name,
        },
        agent: {
          name,
          namespace,
          version,
          url: agentUrl,
        },
        lastMessageAt: new Date(), // TODO: Add to thread metadata?
        messageCount: 0, // TODO: Add to thread metadata?
        url: threadUrl,
      });
    }

    return result;
  }, [accountId, threadsQuery.data]);

  return {
    setThreadData,
    threads,
    threadsQuery,
  };
}
