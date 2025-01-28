'use client';

import { Card } from '@near-pagoda/ui';
import { type z } from 'zod';

import { Code } from '~/components/lib/Code';
import {
  type threadMessageModel,
  type threadMessageModelContentJson,
} from '~/lib/models';

import { protocolSchema } from './protocol/schema';
import { RequestChoice } from './protocol/RequestChoice';

type Props = {
  id: string;
  content: z.infer<typeof threadMessageModelContentJson>;
  role: z.infer<typeof threadMessageModel>['role'];
};

export const JsonMessage = ({ content, id }: Props) => {
  const { json } = content;

  const jsonAsString = () => {
    return JSON.stringify(json, null, 2);
  };

  const protocol = protocolSchema.safeParse(json);

  if (protocol.data) {
    if ('request_choice' in protocol.data) {
      return <RequestChoice content={protocol.data.request_choice} id={id} />;
    }
  } else if (protocol.error) {
    console.warn(
      'JSON message failed to match NEAR AI Protocol message. Will render as JSON codeblock.',
      protocol.error,
    );
  }

  return (
    <Card animateIn>
      <Code bleed language="json" source={jsonAsString()} />
    </Card>
  );
};
