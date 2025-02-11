'use client';

import { Code } from '~/components/lib/Code';

import { useThreadMessageContent } from '../ThreadMessageContentProvider';
import { MessageCard } from './MessageCard';

export const UnknownMessage = () => {
  const { content } = useThreadMessageContent();
  const contentAsJsonString = JSON.stringify(content, null, 2);

  return (
    <MessageCard>
      <Code bleed language="json" source={contentAsJsonString} />
    </MessageCard>
  );
};
