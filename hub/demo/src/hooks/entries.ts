import { useParams, useSearchParams } from 'next/navigation';
import { useMemo, useState } from 'react';
import { type z } from 'zod';

import {
  type entriesModel,
  type EntryCategory,
  type entrySecretModel,
} from '~/lib/models';
import { useAuthStore } from '~/stores/auth';
import { api } from '~/trpc/react';
import { wordsMatchFuzzySearch } from '~/utils/search';

import { useDebouncedValue } from './debounce';

export function useEntryParams() {
  const { namespace, name, version } = useParams();

  return {
    namespace: namespace as string,
    name: name as string,
    version: version as string,
  };
}

export function useCurrentEntry(category: EntryCategory) {
  const { namespace, name, version } = useEntryParams();

  const entriesQuery = api.hub.entries.useQuery({
    category,
    namespace,
    showLatestVersion: false,
  });

  const currentVersions = entriesQuery.data?.filter(
    (item) => item.name === name,
  );

  const currentEntry = currentVersions?.find(
    (item) => item.version === version,
  );

  return {
    currentEntry,
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

export function useCurrentEntryEnvironmentVariables(
  category: EntryCategory,
  excludeQueryParamKeys?: string[],
) {
  const isAuthenticated = useAuthStore((store) => store.isAuthenticated);
  const { currentEntry } = useCurrentEntry(category);
  const searchParams = useSearchParams();
  const secretsQuery = api.hub.secrets.useQuery(
    {},
    {
      enabled: isAuthenticated,
    },
  );

  const result = useMemo(() => {
    const metadataVariablesByKey = currentEntry?.details.env_vars ?? {};
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
      if (!currentEntry) return false;
      return (
        secret.category === currentEntry.category &&
        secret.namespace === currentEntry.namespace &&
        secret.name === currentEntry.name &&
        secret.version === currentEntry.version
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
  }, [currentEntry, searchParams, secretsQuery.data]);

  return result;
}
