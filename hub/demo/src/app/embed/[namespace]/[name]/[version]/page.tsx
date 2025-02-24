'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { AgentRunner } from '~/components/AgentRunner';
import { useEntryParams } from '~/hooks/entries';
import { useQueryParams } from '~/hooks/url';
import { SIGN_IN_CALLBACK_PATH, SIGN_IN_RESTORE_URL_KEY } from '~/lib/auth';

export default function EmbedAgentPage() {
  const router = useRouter();
  const { namespace, name, version } = useEntryParams();
  const { queryParams } = useQueryParams([
    'showThreads',
    'showOutputAndEnvVars',
  ]);
  const showThreads = queryParams.showThreads === 'true';
  const showOutputAndEnvVars = queryParams.showOutputAndEnvVars === 'true';

  useEffect(() => {
    if (location.hash) {
      localStorage.setItem(
        SIGN_IN_RESTORE_URL_KEY,
        `${location.pathname}${location.search}`,
      );
      router.replace(SIGN_IN_CALLBACK_PATH + location.hash);
    }
  }, [router]);

  return (
    <AgentRunner
      namespace={namespace}
      name={name}
      version={version}
      showLoadingPlaceholder={true}
      showThreads={showThreads}
      showOutputAndEnvVars={showOutputAndEnvVars}
    />
  );
}
