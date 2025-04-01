'use client';

import { useEffect } from 'react';

import { AgentRunner } from '@/components/AgentRunner';
import { useCurrentEntryParams } from '@/hooks/entries';
import { useQueryParams } from '@/hooks/url';
import type { Theme } from '@/stores/embed';
import { useEmbedStore } from '@/stores/embed';

export default function EmbedAgentPage() {
  const { queryParams } = useQueryParams(['theme']);
  const { namespace, name, version } = useCurrentEntryParams();
  const setForcedTheme = useEmbedStore((store) => store.setForcedTheme);

  useEffect(() => {
    if (queryParams.theme) {
      setForcedTheme(queryParams.theme as Theme);
    }
  }, [queryParams.theme, setForcedTheme]);

  return (
    <AgentRunner
      namespace={namespace}
      name={name}
      version={version}
      showLoadingPlaceholder={true}
    />
  );
}
