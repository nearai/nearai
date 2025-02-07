'use client';

import { Card, Text } from '@near-pagoda/ui';
import { useRef } from 'react';
import { type z } from 'zod';

import { Code } from '~/components/lib/Code';
import { type threadMessageModel } from '~/lib/models';

import { RequestData } from './aitp/RequestData';
import { RequestDecision } from './aitp/RequestDecision';
import { CURRENT_AGENT_PROTOCOL_SCHEMA, protocolSchema } from './aitp/schema';

type Props = {
  contentId: string;
  content: Record<string, unknown>;
  role: z.infer<typeof threadMessageModel>['role'];
};

export const JsonMessage = ({ content, contentId, role }: Props) => {
  const hasWarned = useRef(false);

  const jsonAsString = () => {
    return JSON.stringify(content, null, 2);
  };

  const protocol = protocolSchema.safeParse(content);

  if (protocol.data) {
    if ('request_decision' in protocol.data) {
      return (
        <RequestDecision
          content={protocol.data.request_decision}
          contentId={contentId}
        />
      );
    }

    if ('request_data' in protocol.data) {
      return (
        <RequestData
          content={protocol.data.request_data}
          contentId={contentId}
        />
      );
    }
  } else if (protocol.error) {
    if (!hasWarned.current) {
      console.warn(
        `JSON message failed to match ${CURRENT_AGENT_PROTOCOL_SCHEMA}. Will render as JSON codeblock.`,
        protocol.error,
      );
      hasWarned.current = true;
    }
  }

  return (
    <Card animateIn>
      <Code bleed language="json" source={jsonAsString()} />

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
