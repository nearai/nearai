import { useDebouncedFunction } from '@nearai/ui';
import { useParams, useSearchParams } from 'next/navigation';
import { useMemo, useState } from 'react';
import { type z } from 'zod';

import {
  type entriesModel,
  type EntryCategory,
  type entryModel,
  type entrySecretModel,
} from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { trpc } from '@/trpc/TRPCProvider';
import { wordsMatchFuzzySearch } from '@/utils/search';

export function useCurrentEntryParams(overrides?: {
  namespace?: string;
  name?: string;
  version?: string;
}) {
  const params = useParams();
  const namespace = decodeURIComponent(
    (overrides?.namespace ?? params.namespace ?? '') as string,
  );
  const name = decodeURIComponent(
    (overrides?.name ?? params.name ?? '') as string,
  );
  const version = decodeURIComponent(
    (overrides?.version ?? params.version ?? '') as string,
  );
  const id = `${namespace}/${name}/${version}`;

  return {
    id,
    namespace,
    name,
    version,
  };
}

export function useCurrentEntry(
  category: EntryCategory,
  options?: {
    enabled?: boolean;
    refetchOnMount?: boolean;
    overrides?: {
      namespace?: string;
      name?: string;
      version?: string;
    };
  },
) {
  const { id, namespace, name, version } = useCurrentEntryParams(
    options?.overrides,
  );

  const entryQuery = trpc.hub.entry.useQuery(
    {
      category,
      name,
      namespace,
      version,
    },
    {
      refetchOnMount: options?.refetchOnMount,
      enabled: typeof options?.enabled === 'boolean' ? options.enabled : true,
    },
  );

  const currentEntry = entryQuery.data?.entry;
  const currentVersions = entryQuery.data?.versions;

  return {
    currentEntry,
    currentEntryId: id,
    currentEntryIsHidden: !!entryQuery.data && !currentEntry,
    currentVersions,
  };
}

export function useEntriesSearch(
  data: z.infer<typeof entriesModel> | undefined,
) {
  const [searchQuery, _setSearchQuery] = useState('');

  const setSearchQuery = useDebouncedFunction((value: string) => {
    _setSearchQuery(value);
  }, 150);

  const searched = useMemo(() => {
    if (!data || !searchQuery) return data;

    return data.filter((item) =>
      wordsMatchFuzzySearch(
        [item.namespace, item.name, ...item.tags],
        searchQuery,
      ),
    );
  }, [data, searchQuery]);

  return {
    searched,
    searchQuery,
    setSearchQuery,
  };
}

export type EntryEnvironmentVariable = {
  key: string;
  metadataValue?: string;
  urlValue?: string;
  secret?: z.infer<typeof entrySecretModel>;
};

export function useEntryEnvironmentVariables(
  entry: z.infer<typeof entryModel> | undefined,
  excludeQueryParamKeys?: string[],
) {
  const auth = useAuthStore((store) => store.auth);
  const searchParams = useSearchParams();
  const secretsQuery = trpc.hub.secrets.useQuery(
    {},
    {
      enabled: !!auth,
    },
  );

  const result = useMemo(() => {
    const metadataVariablesByKey = entry?.details.env_vars ?? {};
    const urlVariablesByKey: Record<string, string> = {};

    searchParams.forEach((value, key) => {
      if (excludeQueryParamKeys?.includes(key)) return;
      urlVariablesByKey[key] = value;
    });

    const variablesByKey: Record<string, EntryEnvironmentVariable> = {};

    Object.entries(metadataVariablesByKey).forEach(([key, value]) => {
      variablesByKey[key] = {
        key,
        metadataValue: value,
      };
    });

    Object.entries(urlVariablesByKey).forEach(([key, value]) => {
      const existing = variablesByKey[key];
      if (existing) {
        existing.urlValue = value;
      } else {
        variablesByKey[key] = {
          key,
          urlValue: value,
        };
      }
    });

    const secrets = secretsQuery.data?.filter((secret) => {
      if (!entry) return false;
      return (
        secret.category === entry.category &&
        secret.namespace === entry.namespace &&
        secret.name === entry.name &&
        (secret.version === entry.version || !secret.version)
      );
    });

    secrets?.forEach((secret) => {
      const existing = variablesByKey[secret.key];
      if (existing) {
        existing.secret = secret;
      } else {
        variablesByKey[secret.key] = {
          key: secret.key,
          secret,
        };
      }
    });

    const variables = Object.values(variablesByKey);
    variables.sort((a, b) => a.key.localeCompare(b.key));

    return {
      metadataVariablesByKey,
      urlVariablesByKey,
      variablesByKey,
      variables,
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entry, searchParams, secretsQuery.data]);

  return result;
}
