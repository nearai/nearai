'use client';

import { AgentRunner } from '@/components/AgentRunner';
import { useCurrentEntryParams } from '@/hooks/entries';

export default function EntryRunPage() {
  const { namespace, name, version } = useCurrentEntryParams();

  return <AgentRunner namespace={namespace} name={name} version={version} />;
}
