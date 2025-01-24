'use client';

import { Card, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import {
  type threadMessageModel,
  type threadMessageModelContentJson,
} from '~/lib/models';

import { Code } from '../lib/Code';

type Props = {
  content: z.infer<typeof threadMessageModelContentJson>;
  role: z.infer<typeof threadMessageModel>['role'];
};

export const JsonMessage = ({ content }: Props) => {
  const { json } = content;

  const jsonAsString = () => {
    return JSON.stringify(json, null, 2);
  };

  return (
    <Card animateIn>
      <Text>Unknown JSON schema in message:</Text>
      <Code language="json" source={jsonAsString()} />
    </Card>
  );
};
