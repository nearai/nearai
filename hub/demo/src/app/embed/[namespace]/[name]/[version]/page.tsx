'use client';

import { AgentRunner } from '~/components/AgentRunner';
import { useEntryParams } from '~/hooks/entries';
import { useQueryParams } from '~/hooks/url';

export default function EmbedAgentPage() {
  const { namespace, name, version } = useEntryParams();
  const { queryParams } = useQueryParams([
    'showThreads',
    'showOutputAndEnvVars',
  ]);
  const showThreads = queryParams.showThreads === 'true';
  const showOutputAndEnvVars = queryParams.showOutputAndEnvVars === 'true';

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
