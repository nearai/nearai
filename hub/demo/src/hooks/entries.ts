import { useParams, useSearchParams } from 'next/navigation';
import { useMemo, useState } from 'react';
import { type z } from 'zod';

import {
  type entriesModel,
  type EntryCategory,
  type entryModel,
  type entrySecretModel,
} from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { wordsMatchFuzzySearch } from '~/utils/search';

import { useDebouncedValue } from './debounce';

export function useEntryParams(overrides?: {
  namespace?: string;
  name?: string;
  version?: string;
}) {
  const params = useParams();
  const namespace = overrides?.namespace ?? params.namespace;
  const name = overrides?.name ?? params.name;
  const version = overrides?.version ?? params.version;
  const id = `${namespace as string}/${name as string}/${version as string}`;

  return {
    id,
    namespace: namespace as string,
    name: name as string,
    version: version as string,
  };
}

export function useCurrentEntry(
  category: EntryCategory,
  overrides?: {
    namespace?: string;
    name?: string;
    version?: string;
  },
) {
  const { id, namespace, name, version } = useEntryParams(overrides);

  const entriesQuery = api.hub.entries.useQuery({
    category,
    namespace,
    showLatestVersion: false,
  });

  const currentVersions = entriesQuery.data?.filter(
    (item) => item.name === name,
  );

  currentVersions?.sort((a, b) => b.id - a.id);

  const currentEntry =
    version === 'latest'
      ? currentVersions?.[0]
      : currentVersions?.find((item) => item.version === version);

  return {
    currentEntry,
    currentEntryId: id,
    currentEntryIsHidden: !!entriesQuery.data && !currentEntry,
    currentVersions,
  };
}

export function useEntriesSearch(
  data: z.infer<typeof entriesModel> | undefined,
) {
  const [searchQuery, setSearchQuery] = useState('');
  const searchQueryDebounced = useDebouncedValue(searchQuery, 150);

  const searched = useMemo(() => {
    if (!data || !searchQueryDebounced) return data;

    return data.filter((item) =>
      wordsMatchFuzzySearch(
        [item.namespace, item.name, ...item.tags],
        searchQueryDebounced,
      ),
    );
  }, [data, searchQueryDebounced]);

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
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const searchParams = useSearchParams();
  const secretsQuery = api.hub.secrets.useQuery(
    {},
    {
      enabled: isAuthenticated,
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
