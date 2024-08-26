import { useQuery } from '@tanstack/react-query';

import { api } from '~/trpc/react';

const PROVIDER_MODEL_SEP = '::';

export function useListModels(provider: string) {
  const listModels = api.hub.listModels.useQuery();

  return useQuery({
    queryKey: ['listModels', provider],
    queryFn: () => {
      const m = listModels.data?.data
        .map((m) => {
          if (!m.supports_chat) {
            return null;
          }
          // filter out models that don't belong to the currently selected provider
          if (!m.id.includes(provider + PROVIDER_MODEL_SEP)) {
            return null;
          }
          return {
            label: m.id.replace(provider + PROVIDER_MODEL_SEP, ''),
            value: m.id,
          };
        })
        .filter(Boolean) as { label: string; value: string }[];

      return m;
    },
    enabled: !!listModels.data,
  });
}
