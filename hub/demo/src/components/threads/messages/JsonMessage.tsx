'use client';

import { Card, Text } from '@near-pagoda/ui';
import { useRef } from 'react';
import { type z } from 'zod';

import { Code } from '~/components/lib/Code';
import { type threadMessageModel } from '~/lib/models';

import { RequestData } from './aitp/RequestData';
import { RequestDecision } from './aitp/RequestDecision';
import { parseJsonWithAitpSchema } from './aitp/schema';
import { CURRENT_AGENT_PROTOCOL_SCHEMA } from './aitp/schema/base';

type Props = {
  contentId: string;
  content: Record<string, unknown>;
  role: z.infer<typeof threadMessageModel>['role'];
};

export const JsonMessage = ({ content, contentId, role }: Props) => {
  const hasWarned = useRef(false);
  const aitp = parseJsonWithAitpSchema(content);

  if ('request_decision' in aitp) {
    return (
      <RequestDecision content={aitp.request_decision} contentId={contentId} />
    );
  } else if ('request_data' in aitp) {
    return <RequestData content={aitp.request_data} contentId={contentId} />;
  }

  if (!hasWarned.current) {
    console.warn(
      `JSON message failed to match ${CURRENT_AGENT_PROTOCOL_SCHEMA}. Will render as JSON codeblock.`,
      aitp.error,
    );
    hasWarned.current = true;
  }

  return (
    <Card animateIn>
      <Code bleed language="json" source={JSON.stringify(content, null, 2)} />

      <Text
        size="text-xs"
        style={{
          textTransform: 'capitalize',
        }}
      >
        - {role}
      </Text>
    </Card>
  );
};
