'use client';

import { Card, Text } from '@near-pagoda/ui';
import { type z } from 'zod';

import { Code } from '~/components/lib/Code';
import {
  type threadMessageContentModel,
  type threadMessageModel,
} from '~/lib/models';

type Props = {
  contentId: string;
  content: z.infer<typeof threadMessageContentModel>;
  role: z.infer<typeof threadMessageModel>['role'];
};

export const UnknownMessage = ({ content, role }: Props) => {
  const contentAsJsonString = JSON.stringify(content, null, 2);

  return (
    <Card animateIn>
      <Code bleed language="json" source={contentAsJsonString} />

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
