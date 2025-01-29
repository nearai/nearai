'use client';

import { Card } from '@near-pagoda/ui';
import { useRef } from 'react';
import { type z } from 'zod';

import { Code } from '~/components/lib/Code';
import {
  type threadMessageModel,
  type threadMessageModelContentJson,
} from '~/lib/models';

import { RequestChoice } from './protocol/RequestChoice';
import { protocolSchema } from './protocol/schema';

type Props = {
  contentId: string;
  content: z.infer<typeof threadMessageModelContentJson>;
  role: z.infer<typeof threadMessageModel>['role'];
};

export const JsonMessage = ({ content, contentId }: Props) => {
  const { json } = content;
  const hasWarned = useRef(false);

  const jsonAsString = () => {
    return JSON.stringify(json, null, 2);
  };

  const protocol = protocolSchema.safeParse(json);

  if (protocol.data) {
    if ('request_choice' in protocol.data) {
      return (
        <RequestChoice
          content={protocol.data.request_choice}
          contentId={contentId}
        />
      );
    }
  } else if (protocol.error) {
    if (!hasWarned.current) {
      console.warn(
        'JSON message failed to match NEAR AI Protocol message. Will render as JSON codeblock.',
        protocol.error,
      );
      hasWarned.current = true;
    }
  }

  return (
    <Card animateIn>
      <Code bleed language="json" source={jsonAsString()} />
    </Card>
  );
};
