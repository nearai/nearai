'use client';

import { Code } from '@/components/lib/Code';

import { useThreadMessageContent } from '../ThreadMessageContentProvider';
import { Message } from './Message';

export const UnknownMessage = () => {
  const { content } = useThreadMessageContent();
  const contentAsJsonString = JSON.stringify(content, null, 2);

  return (
    <Message>
      <Code bleed language="json" source={contentAsJsonString} />
    </Message>
  );
};
