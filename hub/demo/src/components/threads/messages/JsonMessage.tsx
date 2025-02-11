'use client';

import { useRef } from 'react';

import { Code } from '~/components/lib/Code';

import { RequestData } from './aitp/RequestData';
import { RequestDecision } from './aitp/RequestDecision';
import { parseJsonWithAitpSchema } from './aitp/schema';
import { CURRENT_AGENT_PROTOCOL_SCHEMA } from './aitp/schema/base';
import { MessageCard } from './MessageCard';

type Props = {
  json: Record<string, unknown>;
};

export const JsonMessage = ({ json }: Props) => {
  const hasWarned = useRef(false);
  const aitp = parseJsonWithAitpSchema(json);

  if ('request_decision' in aitp) {
    return <RequestDecision content={aitp.request_decision} />;
  } else if ('request_data' in aitp) {
    return <RequestData content={aitp.request_data} />;
  }

  if (!hasWarned.current) {
    console.warn(
      `JSON message failed to match ${CURRENT_AGENT_PROTOCOL_SCHEMA}. Will render as JSON codeblock.`,
      aitp.error,
    );
    hasWarned.current = true;
  }

  return (
    <MessageCard>
      <Code bleed language="json" source={JSON.stringify(json, null, 2)} />
    </MessageCard>
  );
};
