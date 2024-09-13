import { useMemo } from 'react';

import { useAuthStore } from '~/stores/auth';
import { api, type RouterOutputs } from '~/trpc/react';

export type Thread = {
  agent: {
    name: string;
    namespace: string;
    version: string;
    url: string;
  };
  environments: RouterOutputs['hub']['registryEntries'];
  environmentId: string;
  lastMessageAt: Date | null;
  messageCount: number;
};

export function useThreads() {
  const accountId = useAuthStore((store) => store.auth?.account_id);

  const list = api.hub.registryEntries.useQuery(
    {
      category: 'environment',
      namespace: accountId,
    },
    {
      enabled: !!accountId,
    },
  );

  const threads = useMemo(() => {
    const result: Thread[] = [];
    if (!accountId) return [];
    if (!list.data) return;

    // If an environment has a nullish `base_id`, it's a parent (the start of a thread)
    const parents = list.data.filter(
      (environment) => !environment.details.base_id,
    );
    const children = list.data.filter(
      (environment) => !!environment.details.base_id,
    );

    for (const parent of parents) {
      const environments = followThread(children, parent);
      const lastEnvironment = environments.at(-1);

      if (lastEnvironment) {
        const environmentId = `${accountId}/${lastEnvironment.name}/${lastEnvironment.version}`;
        const name = lastEnvironment.details.primary_agent_name;
        const namespace = lastEnvironment.details.primary_agent_namespace;
        const version = lastEnvironment.details.primary_agent_version;

        if (!name || !namespace || !version) continue;

        const url = `/agents/${namespace}/${name}/${version}/run?environmentId=${encodeURIComponent(environmentId)}`;

        result.push({
          agent: {
            name,
            namespace,
            version,
            url,
          },
          environments,
          environmentId,
          lastMessageAt: lastEnvironment.details.timestamp
            ? new Date(lastEnvironment.details.timestamp)
            : null,
          messageCount: environments.length,
        });
      }
    }

    return result;
  }, [accountId, list.data]);

  return {
    threads,
    threadsQuery: list,
  };
}

function followThread(
  children: RouterOutputs['hub']['registryEntries'],
  current: RouterOutputs['hub']['registryEntries'][number],
  result: RouterOutputs['hub']['registryEntries'] = [],
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
