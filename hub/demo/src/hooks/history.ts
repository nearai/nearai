import { useMemo } from 'react';

import { useAuthStore } from '~/stores/auth';
import { api, type RouterOutputs } from '~/trpc/react';

type ChatThread = {
  description: string;
  environmentId: string;
  lastMessageAt: Date | null;
  messageCount: number;
  url: string;
};

export function useAgentChatHistory() {
  const accountId = useAuthStore((store) => store.auth?.account_id);

  const list = api.hub.listRegistry.useQuery(
    {
      category: 'environment',
      namespace: accountId,
    },
    {
      enabled: !!accountId,
    },
  );

  const threads = useMemo(() => {
    const result: ChatThread[] = [];
    if (!list.data) return result;

    // If an environment has a nullish `base_id`, it's a parent (the start of a thread)
    const parents = list.data.filter(
      (environment) => !environment.details.base_id,
    );
    const children = list.data.filter(
      (environment) => !!environment.details.base_id,
    );

    for (const parent of parents) {
      const thread = followThread(children, parent);
      const lastMessage = thread.at(-1);

      if (lastMessage) {
        const environmentId = `${accountId}/${lastMessage.name}/${lastMessage.version}`;
        const description = lastMessage.details.agents?.[0];
        const segments = description?.split('/') ?? [];
        const namespace = segments[0];
        const name = segments[1];
        const version = segments[2];
        const url = `/agents/${namespace}/${name}/${version}/run?environmentId=${encodeURIComponent(environmentId)}`;

        result.push({
          description: description ?? lastMessage.name,
          environmentId,
          lastMessageAt: lastMessage.details.timestamp
            ? new Date(lastMessage.details.timestamp)
            : null,
          messageCount: thread.length,
          url,
        });
      }
    }

    return result;
  }, [list.data]);

  return {
    threads,
    threadsQuery: list,
  };
}

function followThread(
  children: RouterOutputs['hub']['listRegistry'],
  current: RouterOutputs['hub']['listRegistry'][number],
  result: RouterOutputs['hub']['listRegistry'] = [],
) {
  result.push(current);

  const next = children.find(
    (c) =>
      current.details.run_id &&
      c.details.base_id?.includes(current.details.run_id),
  );

  if (next) {
    followThread(children, next, result);
    return result;
  }

  return result;
}
