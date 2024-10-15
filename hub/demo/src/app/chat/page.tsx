'use client';

import { AgentRunner } from '~/components/AgentRunner';
import { ModelRunner } from '~/components/ModelRunner';
import { env } from '~/env';
import { parseEntryId } from '~/lib/entries';

export default function ChatPage() {
  if (env.NEXT_PUBLIC_CONSUMER_MODE && env.NEXT_PUBLIC_CONSUMER_CHAT_AGENT_ID) {
    const { namespace, name, version } = parseEntryId(
      env.NEXT_PUBLIC_CONSUMER_CHAT_AGENT_ID,
    );
    return (
      <AgentRunner
        namespace={namespace}
        name={name}
        version={version}
        showLoadingPlaceholder={true}
      />
    );
  }

  return <ModelRunner />;
}
