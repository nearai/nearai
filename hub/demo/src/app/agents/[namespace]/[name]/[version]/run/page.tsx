'use client';

import { AgentRunner } from '~/components/AgentRunner';
import { useEntryParams } from '~/hooks/entries';

export default function EntryRunPage() {
  const { namespace, name, version } = useEntryParams();

  return <AgentRunner namespace={namespace} name={name} version={version} />;
}
