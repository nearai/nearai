import { useCallback, useMemo } from 'react';
import { type z } from 'zod';

import { type threadModel } from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api, type RouterOutputs } from '~/trpc/react';

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
  const accountId = useAuthStore((store) => store.auth?.account_id);
  const utils = api.useUtils();

  const threadsQuery = api.hub.threads.useQuery(undefined, {
    enabled: !!accountId,
  });

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

    const result: ThreadSummary[] = [];

    for (const data of threadsQuery.data) {
      const rootAgentId = data.metadata.agent_ids?.[0];
      if (!rootAgentId) continue;

      const [namespace, name, version, ...otherSegments] =
        rootAgentId.split('/');
      if (!namespace || !name || !version || otherSegments.length > 0) continue;

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
  }, [accountId, threadsQuery.data]);

  return {
    setThreadData,
    threads,
    threadsQuery,
  };
}
